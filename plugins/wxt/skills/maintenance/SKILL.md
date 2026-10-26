---
name: maintenance
description: Maintain a WXT browser extension — health check (frozen install, wxt prepare, typecheck, entrypoint audit, tests, Chrome + Firefox builds, dependency audit), upgrading WXT across 0.x breaking releases, dev-mode problems (browser not opening, HMR, persistent profile, devcontainers), debugging ("Extension context invalidated", "not implemented", content script not running, styles leaking or rem scaling in shadow root UIs), unit tests with Vitest + fake-browser, E2E with Playwright, testing extension updates and permission changes. Use for "maintenance", "upgrade wxt", "check extension health", "why doesn't my content script run", "add tests".
---

# wxt:maintenance — keeping the extension healthy

For new features use `wxt:entrypoints`; for zips and store releases use `wxt:publish`.

## Start with a health check

```sh
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [project-dir]          # full
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [project-dir] --quick  # no builds, no audit
```

Detects the package manager from the lockfile, then runs the frozen install,
`wxt prepare`, `tsc --noEmit`, the entrypoint audit
(`skills/entrypoints/scripts/audit_entrypoints.py` from this plugin),
`vitest run` when Vitest is installed, `wxt build` for Chrome and Firefox, and
the dependency audit; then lists outdated packages and `ponytail:` markers.

Report a PASS/FAIL list with the proposed fix per FAIL. Apply only what was
asked or is clearly safe (lockfile refresh, `wxt prepare`, moving runtime code
into `main()`); upgrades follow the runbook.

## Common tasks

Exact steps in `references/runbook.md`:

| Task | Summary |
|---|---|
| Upgrade WXT | minor/patch: `pnpm i wxt@latest`; `0.x` bump = breaking: `--ignore-scripts`, apply the version's notes (§1), then `wxt prepare` |
| Dev mode | browser opens only with `web-ext` installed; profiles, binaries, Chrome flags in `web-ext.config.ts` (§2) |
| Debugging | symptom → cause table (§3) |
| Unit tests | Vitest + `WxtVitest()` + `fakeBrowser` (§4) |
| E2E | Playwright with `.output/chrome-mv3` loaded (§4) |
| Update / permission testing | `runtime.onInstalled` reason `update`, Google's update testing tool (§5) |

## Rules

- Never hand-edit `.wxt/` or `.output/`; they are regenerated. Run
  `wxt prepare` after changing `wxt.config.ts`, modules, or auto-import dirs.
- Versions only move forward. A toolchain mismatch is fixed with the right
  Node (≥ 22 for wxt 0.21) or `packageManager`, not by downgrading WXT.
- Commit the lockfile with every dependency change; CI installs frozen.
- Test both targets after any change: Chrome builds MV3, Firefox builds MV2 by default.
