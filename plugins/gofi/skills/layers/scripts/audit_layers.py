#!/usr/bin/env python3
"""Audit a gofi project for layer violations.

Errors (exit code 1):
  - an internal package imports a layer it must not depend on
  - HTTP (fiber) inside models/repositories, database/sql inside handlers/dtos,
    env/flag parsing inside internal/config
  - raw SQL statements outside repositories, seeders, migrations and cmd/
  - a migration without its up/down pair, or a duplicated version number
Warnings:
  - a repository or handler type not registered in its factory.go
  - a handler writing JSON itself instead of the dtos response helpers
  - gaps in migration numbering

usage: python3 audit_layers.py [--root .]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Internal packages each layer may import (paths relative to the module); a
# rule also allows its sub-packages. The single source of truth for the import
# rules: structure.md and SKILL.md only summarize it.
ALLOWED: dict[str, set[str]] = {
    "internal/config": set(),
    "internal/models": set(),
    "internal/lib/apperr": set(),
    "internal/lib/validator": set(),
    "internal/lib/constant": set(),
    "internal/lib": {"migrations"},
    "internal/dtos": {"internal/lib/validator", "internal/lib/apperr", "internal/lib/constant"},
    "internal/repositories": {"internal/models", "internal/lib"},
    "internal/app": {"internal/config", "internal/repositories"},
    "internal/seeders": {"internal/models", "internal/lib"},
    "internal/middlewares": {"internal/app", "internal/config", "internal/dtos", "internal/lib"},
    "internal/handlers": {"internal/app", "internal/dtos", "internal/lib", "internal/models",
                          "internal/repositories"},
    "migrations": set(),
}

FORBIDDEN_EXTERNAL: dict[str, list[tuple[str, str]]] = {
    "internal/models": [("github.com/gofiber/", "models are plain structs, no HTTP")],
    "internal/repositories": [("github.com/gofiber/", "repositories are HTTP-agnostic")],
    "internal/handlers": [("database/sql", "SQL belongs in repositories")],
    "internal/dtos": [("database/sql", "dtos describe HTTP payloads, not rows")],
    "internal/config": [("os", "parse env in cmd/api/flag.go"), ("flag", "parse flags in cmd/api/flag.go")],
}

SQL_RE = re.compile(r"\b(SELECT\s+.+?\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.I | re.S)
SQL_OK = ("internal/repositories", "internal/seeders", "migrations", "cmd/")
IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)^\)", re.M | re.S)
IMPORT_ONE = re.compile(r'^import\s+(?:\w+\s+)?"([^"]+)"', re.M)


def imports_of(src: str) -> list[str]:
    out = IMPORT_ONE.findall(src)
    for block in IMPORT_BLOCK.findall(src):
        out += re.findall(r'"([^"]+)"', block)
    return out


def layer_of(rel: str) -> str | None:
    pkg = str(Path(rel).parent)
    best = None
    for layer in ALLOWED:
        if pkg == layer or pkg.startswith(layer + "/"):
            if best is None or len(layer) > len(best):
                best = layer
    return best


def allowed(layer: str, target: str) -> bool:
    return any(target == rule or target.startswith(rule + "/") for rule in (layer, *ALLOWED[layer]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    gomod = root / "go.mod"
    if not gomod.exists():
        sys.exit(f"{root} has no go.mod")
    module = re.search(r"^module\s+(\S+)", gomod.read_text(), re.M).group(1)

    errors: list[str] = []
    warnings: list[str] = []

    for path in sorted(root.rglob("*.go")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".", "vendor/")) or "/." in rel or rel.endswith("_test.go"):
            continue
        src = path.read_text(encoding="utf-8")
        layer = layer_of(rel)
        if layer:
            for imp in imports_of(src):
                if imp.startswith(module + "/"):
                    target = imp[len(module) + 1:]
                    if not allowed(layer, target):
                        errors.append(f"{rel}: {layer} must not import {target}")
                for prefix, why in FORBIDDEN_EXTERNAL.get(layer, []):
                    if imp == prefix or imp.startswith(prefix.rstrip("/") + "/") and prefix.endswith("/"):
                        errors.append(f"{rel}: imports {imp} ({why})")
        if not rel.startswith(SQL_OK):
            for lit in re.findall(r"`[^`]*`", src):
                if SQL_RE.search(lit):
                    errors.append(f"{rel}: raw SQL outside repositories/seeders: {lit[:60].strip()!r}…")
                    break
        if layer == "internal/handlers" and re.search(r"\.JSON\(", src):
            warnings.append(f"{rel}: writes JSON directly; use dtos.OK/Get/List/Created/Message/Response")

    # Factories
    def check_factory(folder: str, type_re: str, factory_name: str) -> None:
        factory = root / folder / "factory.go"
        if not factory.exists():
            warnings.append(f"{folder}/factory.go missing")
            return
        ftext = factory.read_text()
        for p in sorted((root / folder).glob("*.go")):
            if p.name == "factory.go" or p.name.endswith("_test.go"):
                continue
            for t in re.findall(type_re, p.read_text()):
                if t not in ftext:
                    warnings.append(f"{folder}/{p.name}: {t} is not registered in {factory_name}")

    check_factory("internal/repositories", r"^type (\w+Repository) struct", "Repositories")
    check_factory("internal/handlers", r"^type (\w+Handler) struct", "Handlers")

    # Migrations
    mig = root / "migrations"
    if mig.is_dir():
        versions: dict[int, dict[str, list[str]]] = {}
        for p in mig.glob("*.sql"):
            m = re.match(r"^(\d+)_(.+)\.(up|down)\.sql$", p.name)
            if not m:
                errors.append(f"migrations/{p.name}: name must be NNNNNN_name.(up|down).sql")
                continue
            versions.setdefault(int(m.group(1)), {}).setdefault(m.group(3), []).append(m.group(2))
        for v, kinds in sorted(versions.items()):
            for k in ("up", "down"):
                if k not in kinds:
                    errors.append(f"migrations: version {v} has no .{k}.sql")
                elif len(kinds[k]) > 1:
                    errors.append(f"migrations: version {v} is used by {kinds[k]}")
        nums = sorted(versions)
        if nums and nums != list(range(nums[0], nums[-1] + 1)):
            warnings.append(f"migrations: numbering has gaps {nums}")

    for e in errors:
        print(f"ERROR   {e}")
    for w in warnings:
        print(f"WARN    {w}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
