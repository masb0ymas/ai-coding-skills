#!/usr/bin/env python3
"""Check that every environment variable the code reads is documented.

Sources compared:
  code     envString/envBool/envInt/envDuration("KEY", ...), os.Getenv("KEY"),
           os.LookupEnv("KEY") in non-test .go files
  example  KEY= lines in .env.example (commented "# KEY=" lines count too)

Exit 1 when the code reads a variable that .env.example does not list.

usage: python3 check_env_sync.py [--root .]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CODE_RE = re.compile(r'\b(?:env(?:String|Bool|Int|Duration)|os\.Getenv|os\.LookupEnv)\(\s*"([A-Z][A-Z0-9_]*)"')
EXAMPLE_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=", re.M)
# Read by tests or tooling only, or deliberately refused by the code.
IGNORE = {"TEST_DB_DSN", "AUTHULA_DATABASE_URL"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args().root).resolve()

    code: dict[str, set[str]] = {}
    for p in root.rglob("*.go"):
        rel = p.relative_to(root).as_posix()
        if rel.endswith("_test.go") or rel.startswith((".", "vendor/")):
            continue
        for key in CODE_RE.findall(p.read_text(encoding="utf-8")):
            code.setdefault(key, set()).add(rel)

    example_path = root / ".env.example"
    example = set(EXAMPLE_RE.findall(example_path.read_text())) if example_path.exists() else set()

    missing_example = sorted(k for k in code if k not in example and k not in IGNORE)
    unused_example = sorted(k for k in example if k not in code and k not in IGNORE)

    for k in missing_example:
        print(f"ERROR  {k} is read by {', '.join(sorted(code[k]))} but missing from .env.example")
    for k in unused_example:
        print(f"WARN   {k} is in .env.example but no Go code reads it (read by a library? then ignore)")
    print(f"\n{len(code)} variables read by code, {len(example)} in .env.example")
    sys.exit(1 if missing_example else 0)


if __name__ == "__main__":
    main()
