---
name: maintenance
description: Maintain a vine-style React frontend (vinext on Cloudflare/Docker or Vite + TanStack Router) — health check (lockfile, typecheck, route tree, env sync, layer audit, build, pnpm audit), dependency/React/vinext/TanStack upgrades, shadcn component updates, Node/compatibility-date bumps, env changes, auth/session and API-contract problems, CI. Use for "maintenance", "upgrade dependencies", "check codebase health", "audit vulnerabilities", "login loop", or reviewing a vine app.
---

# vine:maintenance — keeping the app healthy

For new features use `vine:layers`; for images and deploys use `vine:deploy`.

## Start with a health check

```sh
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [app-dir]          # full
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [app-dir] --quick  # no build, no audit
```

Runs `pnpm install --frozen-lockfile`, `tsc --noEmit`, the committed
`routeTree.gen.ts` freshness check (vite), env sync
(`scripts/check_env_sync.py`: every var read in `config/env.ts`,
`next.config.ts`, `vite.config.ts` appears in `.env.example`), the layer audit
(`skills/layers/scripts/audit_layers.py` from this plugin), `pnpm build`, and
`pnpm audit --prod --audit-level high`; then lists `pnpm outdated` and
`ponytail:` markers.

Report a PASS/FAIL list with the proposed fix per FAIL. Apply only what was
asked or is clearly safe (lockfile refresh, route tree regeneration, env
documentation); upgrades follow the runbook.

## Common tasks

Exact steps in `references/runbook.md`:

| Task | Summary |
|---|---|
| Upgrade dependencies | `pnpm update` within ranges first; then one family per commit (vinext, React, TanStack Router, TanStack data, UI, tooling); majors after reading the migration guide |
| Vulnerabilities | `pnpm why`, upgrade the direct dependency, overrides only for transitive fixes |
| shadcn components | several `components/ui` files carry local edits; diff before `--overwrite` |
| Node / Cloudflare runtime | Dockerfile + CI node version together; `compatibilityDate` bumps tested with `pnpm start` (workerd) |
| Env changes | build-time vars → rebuild + redeploy; update env.ts, `.env.example`, Dockerfile ARGs, CF workflow |
| Login loops, 401s, CORS | diagnosis table in runbook §5 |
| API envelope changed | `types/api.ts` + `axios-error.ts` together |

## CI

No workflow ships with vine. For one, copy `assets/ci.yml` to
`.github/workflows/ci.yml` (set `APP_DIR` in a workspace): install, typecheck,
route tree check, build, audit.

## Rules

- Versions only move forward; a local toolchain mismatch is fixed with
  corepack (`packageManager`) or nvm, not by downgrading the app.
- Commit the lockfile with every dependency change; Docker and CI install with
  `--frozen-lockfile`.
