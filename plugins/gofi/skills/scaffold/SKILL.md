---
name: scaffold
description: Generate a new Go REST API codebase with the gofi structure (Fiber v3 + PostgreSQL + Authula auth) — cmd/api, cmd/migrate, internal/{app,config,dtos,lib,middlewares,models,handlers,repositories,seeders}, migrations. Use when the user wants to start/bootstrap/scaffold/generate a new Go backend project, "create a new project", "generate the codebase structure", or a starter based on masb0ymas/gofi.
---

# gofi:scaffold — generate the codebase structure

The main skill for creating a new Go API project with the structure and conventions of
[masb0ymas/gofi](https://github.com/masb0ymas/gofi): Fiber v3, PostgreSQL 18
(pgx + database/sql), golang-migrate with embedded SQL, Authula authentication
embedded as a library, optional Sentry, and a distroless container image.

Other skills in the gofi plugin:

- `gofi:layers` — add new resources/features without breaking the layers.
- `gofi:maintenance` — dependency upgrades, vuln checks, migrations, releases.
- `gofi:deploy` — backend container, SPA served by the backend, or SPA in a separate image.

## Workflow

1. **Gather input.** Three things are needed; ask only for what is still unclear:
   - `--dest` destination folder (must be empty).
   - `--module` Go module path, e.g. `github.com/acme/shop-api`.
   - `--app-name` (optional) project name in lowercase letters/digits/`-`; defaults to the
     last segment of the module. Database name = app name with `-` → `_`.
2. **Run the generator** (Python stdlib only):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/scaffold/scripts/scaffold.py --dest ./shop-api \
     --module github.com/acme/shop-api --owner acme
   ```
   The template is the snapshot shipped with this skill (offline, and always
   matching these docs). Options: `--no-release` (drop release-it + the GitHub Actions workflows),
   `--no-env`, `--no-git-init`, `--force`.
   The script will: copy the template, replace the module path in every import,
   rename the project/database (`APP_NAME`, DSN, seeder advisory lock,
   README, workflows), run `gofmt`, write `.env` with a random `APP_SECRET`
   and `SUPER_USER`, then `git init`.
3. **Verify** in the new folder:
   ```sh
   go mod tidy && go build ./... && go vet ./... && go test ./...
   ```
   Requires Go ≥ 1.27.2 (see `go.mod`). If the local toolchain is older,
   `GOTOOLCHAIN=auto` will download it. Do not lower the `go` version in `go.mod`.
4. **Run locally**: fill in `FROM_ADDRESS` and `RESEND_API_KEY` in `.env`
   (Authula refuses to start without both), set up PostgreSQL 18 (migrations
   use `uuidv7()`, which is new in PG18), then `make run`.
   `MIGRATE_ON_BOOT=true` in `.env.example` applies migrations on boot.
5. **Report** to the user: project location, module, app name, next commands,
   and that `.env` contains generated secrets (already gitignored).

## Generated structure

```
cmd/
  api/          HTTP entrypoint: main.go (wiring), server.go (Fiber + global middleware),
                routes.go (all routes), flag.go (env/flag → config + validation),
                db.go (pool, migrate-on-boot, seed-on-boot), authula.go (auth)
  migrate/      migration CLI: up | down | refresh | force N, --seed
internal/
  app/          Application: dependency container (Config, Logger, DB, Repositories, Auth)
  config/       plain Config struct + env constants; no parsing logic
  dtos/         request payloads (+ Validate) and response envelope {data, metadata, message}
  lib/          cross-layer utils: apperr, validator, constant, db/transaction, migrate, context
  middlewares/  ErrorHandler, Authorization, SuperUser, RateLimit, CrossOrigin, Idempotency
  models/       table structs (Base, SoftDelete) with db/json tags
  handlers/     HTTP handlers per resource + Handlers factory
  repositories/ SQL per table on top of BaseRepository + Repositories factory
  seeders/      idempotent seeders inside a transaction + advisory lock
migrations/     NNNNNN_name.{up,down}.sql, embedded via migrations.go
public/         static files served by Fiber
```

Per-layer responsibilities and dependency rules are in
`references/structure.md`. Do not change this layout when generating; new
features follow the `gofi:layers` skill.

## Built-in starter features

- Authula auth at `/v1/auth` (email+password, magic link, Google OAuth2, JWT
  bearer + session cookie), with a `public.users` table as a mirror + `role` column.
- A complete `categories` CRUD example (list+search+sort+paging, get, create,
  update, soft delete, restore, force delete) — use it as the reference pattern.
- Centralized errors (`apperr` → HTTP status; validation → 422 `{message, errors[]}`).
- Per-IP rate limiting, `Sec-Fetch-Site`-based CSRF protection, idempotency keys
  for writes, helmet, compress, request id, optional Sentry.
- Multi-arch distroless nonroot Dockerfile containing `/app/api` and `/app/migrate`.

## Common variations after generating

See `references/customize.md` for exact steps:

- removing the example `categories` module while keeping its pattern,
- changing the super user name/role, port, CORS origins,
- disabling Google OAuth or Sentry (just leave the env empty),
- notes on removing Authula entirely (a large change; do it incrementally
  and make sure `go build ./...` is green at every step).

## Rules

- Never put secrets in process arguments or in the repo; all settings go through env
  (flags with the same name only override). `.env` must not be committed.
- Keep LICENSE.md (MIT, original copyright masb0ymas) in the generated project.
