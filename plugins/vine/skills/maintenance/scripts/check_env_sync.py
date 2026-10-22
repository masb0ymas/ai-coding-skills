#!/usr/bin/env python3
"""Check that every env var a vine app reads is documented in .env.example.

Read = keys declared in config/env.ts (client/server schemas) plus
process.env.X / import.meta.env.X in next.config.ts and vite.config.ts.
Documented = the name appears anywhere in .env.example (a KEY= line or a comment).

Exit 1 when a read var is undocumented; unused names in .env.example only warn.

Usage: python3 check_env_sync.py --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BUILTIN = {"NODE_ENV", "DEV", "PROD", "MODE", "SSR", "BASE_URL"}
SCHEMA_KEY = re.compile(r"^\s+([A-Z][A-Z0-9_]*):\s*z\b", re.M)
ENV_READ = re.compile(r"\b(?:process\.env|import\.meta\.env)\.([A-Z][A-Z0-9_]*)")
EXAMPLE_KEY = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=", re.M)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    root = Path(p.parse_args().root).resolve()

    env_ts = next((f for f in (root / "src/config/env.ts", root / "config/env.ts") if f.exists()), None)
    if env_ts is None:
        print(f"no config/env.ts under {root}", file=sys.stderr)
        sys.exit(2)
    used = set(SCHEMA_KEY.findall(env_ts.read_text()))
    for cfg in ("next.config.ts", "vite.config.ts"):
        if (root / cfg).exists():
            used |= set(ENV_READ.findall((root / cfg).read_text()))
    used -= BUILTIN

    example = root / ".env.example"
    text = example.read_text() if example.exists() else ""
    missing = sorted(name for name in used if not re.search(rf"\b{name}\b", text))
    unused = sorted(set(EXAMPLE_KEY.findall(text)) - used)

    for name in missing:
        print(f"ERROR  {name} is read but not documented in .env.example")
    for name in unused:
        print(f"WARN   {name} is in .env.example but nothing reads it")
    print(f"{len(used)} env vars read, {len(missing)} undocumented")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
