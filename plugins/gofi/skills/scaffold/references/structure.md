# gofi structure — full map

## Request flow

```
HTTP → Fiber (server.go: recover, logger, helmet, requestid, compress, sentry?,
        CrossOrigin, cors?, static ./public)
     → routes.go (group /v1 + RateLimit, per-route: Authorization → SuperUser → Idempotency)
     → handlers/<resource>.go   (bind+validate dtos, call repository, render dtos.*)
     → repositories/<resource>.go (parameterized SQL via BaseRepository)
     → PostgreSQL
error anywhere → return err → middlewares.ErrorHandler → JSON {message} / 422 {message, errors}
```

## Boot (cmd/api/main.go)

1. `parseFlag` — env → `config.Config`, fatal validation (secret ≥ 32, DSN, CORS origin, etc.).
2. `slog` default logger (debug when `DEBUG=true`, rejected in production).
3. `MIGRATE_ON_BOOT` → `migrateUp` on a dedicated connection (the migrator closes its DB).
4. API pool (`connectDB`) — the connection budget is split in half with the Authula pool.
5. `repositories.New(db)` → `newAuth` (Authula + its own migrations) → `Reconcile` users mirror.
6. `SEED_ON_BOOT` → `seeders.All(db)` + `SuperUserSeeder`.
7. `serve(&app.Application{...})` — graceful shutdown on SIGINT/SIGTERM.

## Per-folder responsibilities

| Folder | Contents | May import (internal) |
|---|---|---|
| `cmd/api` | wiring, server, routes, flag, auth | everything |
| `cmd/migrate` | migration + seed CLI | `lib`, `seeders` |
| `internal/config` | Config struct, Env* constants, cookie names | — |
| `internal/app` | `Application` (dependency container) | `config`, `repositories` |
| `internal/models` | table row structs, `Base`, `SoftDelete` | — |
| `internal/dtos` | request body/query + `Validate`, response envelope | `lib/validator`, `lib/apperr`, `lib/constant` |
| `internal/lib` | `OpenDB`, `WithTransaction`, `NewMigrator`, `ValidateRequest*`, context UID | `lib*`, `migrations` |
| `internal/lib/apperr` | `Error{Kind,Message}`, sentinels, `From` | — |
| `internal/lib/validator` | `MapValidator` + rules (Required, String, MaxLen, Regex) | — |
| `internal/lib/constant` | domain constants (roles, seed ids) | — |
| `internal/repositories` | SQL per table, list/where/sort/count helpers | `models`, `lib*` |
| `internal/handlers` | HTTP handlers per resource + `Handlers` factory | `app`, `dtos`, `lib*`, `models`, `repositories` |
| `internal/middlewares` | ErrorHandler, auth, rate limit, CSRF, idempotency | `app`, `config`, `dtos`, `lib*` |
| `internal/seeders` | idempotent `Seeder`s | `models`, `lib*` |
| `migrations` | ordered SQL + `embed.FS` | — |

Import-direction violations are checked by `skills/layers/scripts/audit_layers.py` in the gofi plugin.
Its `ALLOWED` table is the source of truth; this column is a summary (`lib*` = `internal/lib` and its sub-packages).

## Conventions used throughout the code

- IDs: `uuid.NewV7()` in handlers, `uuidv7()` column default in SQL.
- Required columns on domain tables: `id, created_at, updated_at` (+ `deleted_at` for soft delete),
  indexes on `created_at`, `deleted_at`, and search columns.
- Responses: `dtos.List` (`{data, metadata:{total,offset,limit}, message}`), `dtos.Get`,
  `dtos.Created`, `dtos.OK`, `dtos.Message`.
- Errors: return `apperr.New(apperr.KindX, ...)` or a sentinel; never write error JSON by hand.
- List queries: `dtos.ListQuery` (offset, limit ≤ 100, search, sorted `column:asc|desc`
  whitelisted by the repository).
- Comments explain *why*, not *what*; the `ponytail:` marker flags deliberate limitations
  (e.g. a per-replica in-memory store).
