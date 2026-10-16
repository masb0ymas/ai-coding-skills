---
name: maintenance
description: Maintain a gofi-style Go API (Fiber v3, PostgreSQL, golang-migrate, Authula) — health check (gofmt, vet, tests, govulncheck, layer audit, env/.env.example sync), dependency and Go version upgrades, dirty migration repair, secret rotation, scale-out limits, CI and release-it releases. Use for "maintenance", "upgrade dependency", "check codebase health", "migration dirty", "rotate secrets", "safe refactor", or reviewing a gofi project.
---

# gofi:maintenance — maintaining the codebase

Use for maintenance work on gofi-structured projects. To add
features use `gofi:layers`; for containers/deploys use `gofi:deploy`.

## Start with a health check

```sh
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [project-dir]          # full
bash ${CLAUDE_PLUGIN_ROOT}/skills/maintenance/scripts/health.sh [project-dir] --quick  # without -race & govulncheck
```

Runs: gofmt, `go mod verify`, `go mod tidy` (fails if it changes files),
build, vet, test (`-race`), `govulncheck@v1.8.0`, env sync
(`scripts/check_env_sync.py`), the layer audit (using
`skills/layers/scripts/audit_layers.py` from this plugin),
and lists `ponytail:` markers. Set `TEST_DB_DSN` to a throwaway PostgreSQL 18
database so the `cmd/api` integration tests run too (that database gets wiped).

Report results to the user as a PASS/FAIL list with proposed
fixes; only fix what was asked for or what is clearly safe (formatting, tidy,
env documentation).

## Common tasks

Exact steps are in `references/runbook.md` (`<plugin-root>` there means
`${CLAUDE_PLUGIN_ROOT}`):

| Task                 | Summary                                                                                                                                        |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Upgrade dependencies | patches first (`go get -u=patch ./...`), minor/major one family per commit, read Fiber/Authula release notes, health check + integration tests |
| Bump the Go version  | `go.mod` + the `golang:1.X-alpine` image in the Dockerfile + README                                                                            |
| Dirty migration      | fix the cause → `make db/migrations/force version=N-1` → reboot                                                                                |
| Schema changes       | always a new migration; never edit/renumber deployed ones                                                                                      |
| Secret rotation      | `APP_SECRET` invalidates all JWTs; `SUPER_USER` + `SEED_ON_BOOT` resets the password & sessions                                                |
| Scale out            | move in-memory storage (rate limit, idempotency) to Redis; compute the DB connection budget                                                    |
| Release              | Actions → Release Prepare → merge PR → tag + ghcr image                                                                                        |
| Boot errors          | diagnosis table in runbook section 7                                                                                                           |

## CI

Upstream gofi has no per-push workflow. If the user wants one, copy
`assets/ci.yml` to `.github/workflows/ci.yml` (gofmt, tidy, vet, tests with a
postgres:18 service, govulncheck, docker build).

## Safe refactoring principles

- Keep behavior changes and structural changes in separate commits.
- Preserve the HTTP contract: the `{data, metadata, message}` envelope, statuses from
  `apperr`, 422 `{message, errors[]}` for validation — web clients depend on them.
- Do not delete comments explaining security reasoning (CSRF, rate limit, tokens, connection
  pool) during a refactor; update them if the behavior changes.
- Every new env: `cmd/api/flag.go` + `validateFlag` + `.env.example` + README;
  `check_env_sync.py` fails if `.env.example` falls behind.
- Never downgrade Go/dependency versions to suit a local toolchain; use
  `GOTOOLCHAIN=auto`.
