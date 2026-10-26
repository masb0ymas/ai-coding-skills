#!/usr/bin/env python3
"""Compare the manifest of the old build with the one WXT generates.

Errors (exit 1) — the new manifest asks users for more than the old one:
  - permissions, optional permissions, or host permissions that were not there
  - content script match patterns that were not there
  - a different manifest_version
Warnings — check each one:
  - permissions, host permissions, or content script matches that disappeared
  - name / version / key / gecko id / default_locale changed
  - other top-level fields added, removed, or changed (commands, CSP, ...)
File paths (js/css/html names) are ignored: they legitimately change.

Usage: python3 compare_manifests.py OLD_MANIFEST NEW_MANIFEST
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Keys that only name built files; differences are expected after a migration.
PATH_KEYS = {
    "background", "content_scripts", "action", "browser_action", "page_action",
    "options_page", "options_ui", "side_panel", "sidebar_action", "devtools_page",
    "chrome_url_overrides", "sandbox", "icons", "web_accessible_resources",
}
IDENTITY_KEYS = ("name", "version", "version_name", "key", "default_locale")


def is_host(p: str) -> bool:
    return "://" in p or p == "<all_urls>"


def grants(m: dict) -> dict[str, set[str]]:
    """Permission-like sets, normalised across MV2 (hosts inside permissions) and MV3."""
    perms = set(m.get("permissions", []))
    optional = set(m.get("optional_permissions", []))
    hosts = {p for p in perms if is_host(p)} | set(m.get("host_permissions", []))
    opt_hosts = {p for p in optional if is_host(p)} | set(m.get("optional_host_permissions", []))
    war = set()
    for entry in m.get("web_accessible_resources", []):
        if isinstance(entry, dict):
            war |= {f"{r} @ {match}" for r in entry.get("resources", []) for match in entry.get("matches", ["*"])}
        else:
            war.add(f"{entry} @ *")
    return {
        "permissions": perms - hosts,
        "optional_permissions": optional - opt_hosts,
        "host_permissions": hosts,
        "optional_host_permissions": opt_hosts,
        "content script matches": {p for cs in m.get("content_scripts", []) for p in cs.get("matches", [])},
        "web_accessible_resources": war,
    }


def gecko_id(m: dict) -> str | None:
    return (m.get("browser_specific_settings") or m.get("applications") or {}).get("gecko", {}).get("id")


def compare(old: dict, new: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if old.get("manifest_version") != new.get("manifest_version"):
        errors.append(f"manifest_version {old.get('manifest_version')} -> {new.get('manifest_version')} "
                      f"(build with --mv{old.get('manifest_version')} or compare the matching target)")

    old_g, new_g = grants(old), grants(new)
    for kind in old_g:
        added, removed = new_g[kind] - old_g[kind], old_g[kind] - new_g[kind]
        # Resource paths change with the build tool, so new ones are only worth a warning.
        bucket = warnings if kind == "web_accessible_resources" else errors
        for item in sorted(added):
            bucket.append(f"{kind}: added {item}")
        for item in sorted(removed):
            warnings.append(f"{kind}: removed {item}")

    for key in IDENTITY_KEYS:
        if old.get(key) != new.get(key):
            warnings.append(f"{key}: {old.get(key)!r} -> {new.get(key)!r}")
    if gecko_id(old) != gecko_id(new):
        warnings.append(f"browser_specific_settings.gecko.id: {gecko_id(old)!r} -> {gecko_id(new)!r}")

    skip = PATH_KEYS | set(IDENTITY_KEYS) | {
        "manifest_version", "permissions", "optional_permissions", "host_permissions",
        "optional_host_permissions", "browser_specific_settings", "applications",
    }
    for key in sorted((set(old) | set(new)) - skip):
        if key not in new:
            warnings.append(f"{key}: missing in the new manifest")
        elif key not in old:
            warnings.append(f"{key}: new in the new manifest")
        elif old[key] != new[key]:
            warnings.append(f"{key}: changed {json.dumps(old[key])} -> {json.dumps(new[key])}")

    return errors, warnings


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1])
        return 2
    old, new = (json.loads(Path(p).read_text()) for p in sys.argv[1:])
    errors, warnings = compare(old, new)
    for e in errors:
        print(f"ERROR  {e}")
    for w in warnings:
        print(f"WARN   {w}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
