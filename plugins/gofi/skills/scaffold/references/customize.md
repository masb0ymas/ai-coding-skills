# Customizing after generating

Finish every step with `gofmt -l . && go build ./... && go vet ./... && go test ./...`.

## Removing the example `categories` module

Do this only if the user asks. Its CRUD pattern should first be used for the
first real resource (see the `gofi:layers` skill) before the example is removed.

1. Delete the files:
   `internal/{dtos,handlers,models,repositories,seeders}/category.go`,
   `internal/lib/constant/category.go`.
2. `internal/handlers/factory.go` — remove the `Category` field and its initialization.
3. `internal/repositories/factory.go` — remove the `Category` field and its initialization.
4. `internal/seeders/run.go` — `All` returns `[]Seeder{}` (or other seeders).
5. `cmd/api/routes.go` — remove the `categories := v1.Group(...)` block. If there are no
   other write routes, also remove `idempotent := middlewares.Idempotency()`
   (an unused variable is a compile error). Keep the `v1` group.
6. Migrations:
   - Project has **never** been migrated in any environment: delete
     `000001_create_categories.*` and renumber the rest (000002→000001, 000003→000002).
   - Already migrated somewhere: **do not** delete/renumber; create a new migration
     `drop_categories` (`DROP TABLE IF EXISTS "categories";` / down = recreate it).
7. `cmd/api/integration_test.go` — the "Category writes" block (role check,
   idempotency, CSRF, revocation) tests the middleware through `/v1/categories`.
   Move those tests to the user's first write resource; do not just
   delete them. `middlewares/idempotency_test.go` only uses path strings and
   needs no change.

## Settings that only need env

| Need | How |
|---|---|
| Disable Google sign-in | leave `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` empty |
| Disable Sentry | leave `SENTRY_DSN` empty |
| Change port | `PORT` (also `EXPOSE` in the Dockerfile if changed permanently) |
| Browser origins | `CORS_ALLOWED_ORIGINS` (origins only, no path, no `*`) |
| Behind a reverse proxy | `TRUSTED_PROXIES` = proxy IP/CIDR |
| Change the super user | `SUPER_USER=email:password` (12–128 characters) + `SEED_ON_BOOT=true` |

## Adding new configuration

1. A field in the right struct in `internal/config/config.go`.
2. `flag.XxxVar(&cfg..., "flag-name", envXxx("ENV_NAME", default), "description")` in `cmd/api/flag.go`.
3. Fatal validation in `validateFlag` if the value can be wrong.
4. Document it in `.env.example` (with a comment) and the README table.

## Removing Authula (a large change)

Not part of the skill's default; do it only if the user explicitly asks, incrementally:
1. Switch write routes to a replacement auth middleware that still calls
   `lib.ContextSetUID` (Idempotency needs the UID).
2. Delete `cmd/api/authula.go`, the `/v1/auth` mount, the `Auth` field in `app.Application`,
   `config.ConfigAuth` + its flags, `SuperUserSeeder`, and the users mirror/reconcile.
3. Decide what happens to the `users`/`authula` schema migrations (a new migration, not an edit of an old one).
4. `go mod tidy` to drop the Authula dependencies.
