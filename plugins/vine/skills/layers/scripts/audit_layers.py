#!/usr/bin/env python3
"""Check that a vine-style frontend keeps its layers.

Errors (exit 1):
  - UI (components, app pages, routes, hooks) talks to the API directly
    (axios, lib/api/client-fetch, lib/api/resource, lib/api/services)
    instead of through lib/api/queries
  - services import React/TanStack Query or the layers above them
  - queries import UI or bypass services (axios, client-fetch, resource)
  - dtos import anything but zod and lib/validation-style helpers
  - models contain runtime imports (they are types only)
  - code from the other framework: next/* or vinext in a vite app,
    @tanstack/react-router in a vinext app
  - env read outside config/env.ts (except NODE_ENV / DEV / PROD / MODE and
    the next.config / vite.config files)
  - vinext: a page/layout under app/ uses React hooks without 'use client'
Warnings:
  - a service, query or model file that is not registered in its index.ts

Usage: python3 audit_layers.py --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"""^\s*(import|export)\s+(type\s+)?[^'"]*?from\s+['"]([^'"]+)['"]""", re.M)
SIDE_IMPORT_RE = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.M)
ENV_RE = re.compile(r"\b(?:process\.env|import\.meta\.env)\.([A-Z_][A-Z0-9_]*)")
HOOK_RE = re.compile(r"\buse(?:State|Effect|Memo|Callback|Ref|Reducer|Context|Transition|Router|Pathname|SearchParams|Query|Mutation)\b\s*\(")
ENV_OK = {"NODE_ENV", "DEV", "PROD", "MODE", "SSR", "BASE_URL"}
CONFIG_FILES = {"next.config.ts", "vite.config.ts", "cloudflare.config.ts"}

UI = {"components", "app", "routes", "hooks"}
API_DIRECT = {"services", "client", "resource"}
FORBIDDEN_LAYERS = {
    **{ui: API_DIRECT for ui in UI},
    "services": UI | {"queries"},
    "queries": UI | {"client", "resource"},
    "dtos": UI | API_DIRECT | {"queries", "models"},
}
FORBIDDEN_PACKAGES = {
    **{ui: ("axios",) for ui in UI},
    "services": ("react", "@tanstack/react-query"),
    "queries": ("axios",),
    "dtos": ("react", "axios", "@tanstack/"),
}


def layer_of(rel: str) -> str | None:
    for prefix, layer in (
        ("lib/api/services/", "services"), ("lib/api/queries/", "queries"),
        ("lib/api/models/", "models"), ("lib/api/dtos/", "dtos"),
        ("lib/api/client-fetch", "client"), ("lib/api/resource", "resource"),
        ("components/", "components"), ("app/", "app"), ("routes/", "routes"), ("hooks/", "hooks"),
    ):
        # The bare directory is its index.ts (`@/lib/api/services`).
        if rel.startswith(prefix) or rel == prefix.rstrip("/"):
            return layer
    return None


def resolve(spec: str, src: Path, base: Path) -> str | None:
    """Path of an internal import relative to base, or None for packages."""
    if spec.startswith(("@/", "#/")):
        target = base / spec[2:]
    elif spec.startswith("."):
        target = (src.parent / spec).resolve()
    else:
        return None
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    root = Path(p.parse_args().root).resolve()
    if (root / "src" / "routes" / "__root.tsx").exists():
        kind, base = "vite", root / "src"
    elif (root / "app" / "layout.tsx").exists():
        kind, base = "vinext", root
    else:
        print(f"{root}: not a vine app (no src/routes/__root.tsx or app/layout.tsx)", file=sys.stderr)
        sys.exit(2)

    errors: list[str] = []
    warnings: list[str] = []
    skip = {"node_modules", "dist", ".vinext", ".cloudflare", ".wrangler"}
    files = [f for f in base.rglob("*.ts*") if not skip & set(f.relative_to(root).parts)
             and f.suffix in (".ts", ".tsx") and not f.name.endswith(".gen.ts")]

    for f in sorted(files):
        rel = f.relative_to(base).as_posix()
        where = f.relative_to(root).as_posix()
        text = f.read_text(encoding="utf-8")
        layer = layer_of(rel)
        specs = [(m.group(3), bool(m.group(2))) for m in IMPORT_RE.finditer(text)]
        specs += [(s, False) for s in SIDE_IMPORT_RE.findall(text)]

        for spec, type_only in specs:
            if kind == "vite" and (spec == "vinext" or spec.startswith(("next/", "vinext/"))):
                errors.append(f"{where}: imports {spec} in a vite app (use @tanstack/react-router)")
            if kind == "vinext" and spec.startswith("@tanstack/react-router"):
                errors.append(f"{where}: imports {spec} in a vinext app (use next/link, next/navigation)")
            if layer == "models":
                if not type_only:
                    errors.append(f"{where}: models are types only; use `import type` for {spec}")
                continue
            target = resolve(spec, f, base)
            target_layer = layer_of(target) if target else None
            if target_layer and target_layer in FORBIDDEN_LAYERS.get(layer, ()) and not type_only:
                errors.append(f"{where}: {layer} must not import {target_layer} ({spec})")
            if target is None and any(spec == pkg or spec.startswith(pkg.rstrip("/") + "/") or
                                      (pkg.endswith("/") and spec.startswith(pkg))
                                      for pkg in FORBIDDEN_PACKAGES.get(layer, ())) and not type_only:
                errors.append(f"{where}: {layer} must not import {spec}")

        if f.name not in CONFIG_FILES and rel != "config/env.ts":
            for name in sorted(set(ENV_RE.findall(text)) - ENV_OK):
                errors.append(f"{where}: reads env {name} directly; add it to config/env.ts and import env")

        if kind == "vinext" and layer == "app" and f.name in ("page.tsx", "layout.tsx"):
            if HOOK_RE.search(text) and not re.match(r"""\s*['"]use client['"]""", text):
                errors.append(f"{where}: uses React hooks without 'use client'; move the UI into a client "
                              "component under components/block")

    # Registries: every service/query/model file should be reachable from its index.
    api = base / "lib" / "api"
    for layer, needle in (("services", "from './{}'"), ("queries", "from './{}'"), ("models", "import('./{}')")):
        index = api / layer / "index.ts"
        if not index.exists():
            continue
        registry = index.read_text()
        for f in sorted((api / layer).glob("*.ts")):
            if f.name != "index.ts" and needle.format(f.stem) not in registry:
                warnings.append(f"{f.relative_to(root)}: not registered in lib/api/{layer}/index.ts")

    for e in errors:
        print(f"ERROR  {e}")
    for w in warnings:
        print(f"WARN   {w}")
    print(f"\n{kind} app: {len(files)} files, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
