#!/usr/bin/env python3
"""Catch the WXT mistakes the docs warn about, before the build does.

Errors (exit 1):
  - a JS/TS entrypoint without `export default define{Background,ContentScript,UnlistedScript}`
    (usually a helper file left loose in entrypoints/)
  - runtime code (browser., chrome., document., window.) at the top level of a
    JS/TS entrypoint instead of inside main(); WXT imports it in Node to read options
  - an entrypoint nested two levels deep, or a folder without an index file
  - two entrypoints with the same name (popup.html + popup.ts)
  - import.meta.env.X that is neither WXT_/VITE_ prefixed nor a built-in
    (undefined at runtime)
  - storage used without the "storage" permission in wxt.config.ts
  - a history-mode router (BrowserRouter, createWebHistory, ...) in an extension page
Warnings:
  - injectScript / createIframeUi target not mentioned in web_accessible_resources
  - world: 'MAIN' content scripts (MV3 Chromium only, no extension APIs)
  - TanStack createRouter without createHashHistory

Usage: python3 audit_entrypoints.py --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

JS_EXT = {".ts", ".tsx", ".js", ".jsx"}
ENTRY_EXT = JS_EXT | {".html", ".css", ".scss", ".sass", ".less", ".styl", ".stylus"}
SKIP_DIRS = {"node_modules", ".output", ".wxt", ".git", "dist"}
SRC_DIRS = ("entrypoints", "components", "composables", "hooks", "utils")

DEFINE_RE = re.compile(r"export\s+default\s+define(Background|ContentScript|UnlistedScript)\s*\(")
TOP_LEVEL_RUNTIME_RE = re.compile(r"\b(browser|chrome|document|window)\.")
ENV_RE = re.compile(r"\bimport\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)")
ENV_BUILTIN = {
    "MANIFEST_VERSION", "BROWSER", "CHROME", "FIREFOX", "SAFARI", "EDGE", "OPERA",
    "COMMAND", "ENTRYPOINT", "MODE", "DEV", "PROD", "SSR", "BASE_URL",
}
STORAGE_RE = re.compile(r"\bstorage\.(defineItem|getItem|getItems|setItem|setItems|removeItem|removeItems|watch|getMeta|setMeta)\b|\b(browser|chrome)\.storage\.")
DEFINITION_RE = re.compile(r"=>|^(export\s+)?(async\s+)?function\b")
HISTORY_ROUTER_RE = re.compile(r"\b(createBrowserRouter|BrowserRouter|createWebHistory|createBrowserHistory)\b")
TANSTACK_ROUTER_RE = re.compile(r"\bcreateRouter\s*\(")
MAIN_WORLD_RE = re.compile(r"""\bworld\s*:\s*['"]MAIN['"]""")
INJECT_RE = re.compile(r"""\binjectScript\s*\(\s*['"]/?([^'"]+)['"]""")
IFRAME_RE = re.compile(r"""\bpage\s*:\s*['"]/?([^'"]+\.html)['"]""")


def config_value(config: str, key: str, default: str) -> str:
    m = re.search(rf"""\b{key}\s*:\s*['"]([^'"]+)['"]""", config)
    return m.group(1) if m else default


def entrypoint_name(path: Path, entry_dir: Path) -> str:
    """WXT's rule: the relative path up to the first '.' or '/'."""
    return re.split(r"[./]", path.relative_to(entry_dir).as_posix(), maxsplit=1)[0]


def top_level_runtime(text: str) -> list[int]:
    """Line numbers of column-0 statements touching browser globals.

    ponytail: indentation heuristic, not a parser; formatted code (prettier) keeps
    main() bodies indented, so column-0 lines are top-level statements.
    """
    hits = []
    in_template = False
    for i, line in enumerate(text.splitlines(), 1):
        starts_in_template = in_template
        in_template ^= line.count("`") % 2 == 1
        if starts_in_template or not line or line[0] in " \t}/*)]" or line.startswith(("import ", "export default", "export type", "type ", "interface ")):
            continue
        # Functions defined at the top level only run when main() calls them.
        if DEFINITION_RE.search(line):
            continue
        if TOP_LEVEL_RUNTIME_RE.search(line):
            hits.append(i)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args().root).resolve()

    config_path = next((root / n for n in ("wxt.config.ts", "wxt.config.mts", "wxt.config.js") if (root / n).exists()), None)
    if config_path is None:
        print(f"no wxt.config.ts in {root}")
        return 2
    config = config_path.read_text()
    src = root / config_value(config, "srcDir", ".")
    entry_dir = src / config_value(config, "entrypointsDir", "entrypoints")
    if not entry_dir.is_dir():
        print(f"no entrypoints directory at {entry_dir}")
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    rel = lambda p: p.relative_to(root).as_posix()

    # Entrypoint files: entrypoints/<file> and entrypoints/<dir>/index.<ext>.
    entries: list[Path] = []
    for child in sorted(entry_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_file() and child.suffix in ENTRY_EXT:
            entries.append(child)
        elif child.is_dir():
            index = [p for p in child.iterdir() if p.is_file() and p.stem == "index" and p.suffix in ENTRY_EXT]
            # An index.html is the entrypoint; the folder's index.ts is then just its script.
            if any(p.suffix == ".html" for p in index):
                index = [p for p in index if p.suffix == ".html"]
            if not index:
                errors.append(f"{rel(child)}/: no index file, so WXT silently skips it "
                              f"(entrypoints are one level deep; use '{child.name}.content/index.ts' style names, "
                              f"shared code goes in components/ or utils/)")
            entries.extend(index)

    seen: dict[str, Path] = {}
    for path in entries:
        name = entrypoint_name(path, entry_dir)
        if name in seen:
            errors.append(f"{rel(path)}: same entrypoint name '{name}' as {rel(seen[name])}; "
                          f"put related files in a '{name}/' folder next to one index file, "
                          f"and import CSS from the script instead of a sibling .css entrypoint")
        seen[name] = path

        if path.suffix not in JS_EXT:
            continue
        text = path.read_text(errors="replace")
        if not DEFINE_RE.search(text):
            errors.append(f"{rel(path)}: no `export default defineBackground/defineContentScript/defineUnlistedScript(...)`; "
                          f"helper modules belong in utils/ or next to an index file inside a folder")
        for line in top_level_runtime(text):
            errors.append(f"{rel(path)}:{line}: runtime API at module top level; move it inside main() "
                          f"(it runs in Node at build time, where unimplemented fake-browser APIs throw)")
        if MAIN_WORLD_RE.search(text):
            warnings.append(f"{rel(path)}: world 'MAIN' is MV3/Chromium only and has no extension APIs; "
                            f"prefer injectScript() of an unlisted script")

    # Whole-source checks.
    sources = [
        p for d in {src / n for n in SRC_DIRS} | {src / "app.config.ts"} if d.exists()
        for p in ([d] if d.is_file() else d.rglob("*"))
        if p.is_file() and p.suffix in JS_EXT | {".mts", ".mjs", ".vue", ".svelte"} and not SKIP_DIRS & set(p.parts)
    ]
    uses_storage = None
    for path in sources:
        text = path.read_text(errors="replace")
        for m in ENV_RE.finditer(text):
            name = m.group(1)
            if name not in ENV_BUILTIN and not name.startswith(("WXT_", "VITE_")):
                line = text.count("\n", 0, m.start()) + 1
                errors.append(f"{rel(path)}:{line}: import.meta.env.{name} is undefined at runtime; prefix it with WXT_")
        if uses_storage is None and STORAGE_RE.search(text):
            uses_storage = path
        m = HISTORY_ROUTER_RE.search(text)
        if m:
            errors.append(f"{rel(path)}: {m.group(1)} uses history mode; extension pages need hash routing "
                          f"(createHashRouter / createWebHashHistory / createHashHistory)")
        if TANSTACK_ROUTER_RE.search(text) and "@tanstack/" in text and "createHashHistory" not in text:
            warnings.append(f"{rel(path)}: TanStack createRouter without createHashHistory(); pass history: createHashHistory()")
        for target in INJECT_RE.findall(text) + IFRAME_RE.findall(text):
            if Path(target).name not in config:
                warnings.append(f"{rel(path)}: '{target}' is not in web_accessible_resources in {config_path.name}")

    if uses_storage and not re.search(r"""['"]storage['"]""", config):
        errors.append(f"{rel(uses_storage)}: uses storage but 'storage' is not in manifest.permissions in {config_path.name}")

    for e in errors:
        print(f"ERROR  {e}")
    for w in warnings:
        print(f"WARN   {w}")
    print(f"\n{len(entries)} entrypoints, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
