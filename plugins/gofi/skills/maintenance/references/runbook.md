# gofi maintenance runbook

## 1. Upgrading dependencies

```sh
go list -m -u all | grep '\[' # see what has newer versions
go get -u=patch ./...          # safe: patches only
go get github.com/gofiber/fiber/v3@latest   # minor/major: one at a time
go mod tidy
bash <plugin-root>/skills/maintenance/scripts/health.sh
```
- Bump one dependency family per commit (`chore(deps): bump fiber to vX`)
  so it is easy to revert.
- **Fiber v3**: read the release notes; changes often land in middleware config
  (`static`, `limiter`, `idempotency`, `cors`, `helmet`) and the `Ctx` signature.
- **Authula**: check for changes to route mapping, plugin config, and the
  `authula.*` table schema (created by Authula at boot). Run the integration tests
  (`TEST_DB_DSN`) — they are the only thing that tests the auth flow end to end.
- **golang-migrate / pgx**: the `pgx/v5` driver in `lib/migrate.go` must be the same
  family as `jackc/pgx/v5` in `lib/db.go`.
- `govulncheck` findings that point at functions actually called = priority.

## 2. Bumping the Go version

Change these together, then run the health check:
1. `go.mod` → `go 1.X.Y` (and `toolchain` if used).
2. `Dockerfile` → `FROM --platform=$BUILDPLATFORM golang:1.X-alpine AS build`.
3. Workflows use `go-version-file: go.mod`, so they follow automatically.
4. README *Run* section (minimum version).

## 3. Database migrations

| Situation | Action |
|---|---|
| Adding a schema change | a **new** migration; never edit a migration that is already deployed |
| Boot fails with "migration N failed and left the schema dirty" | fix the cause (SQL/data), make sure the schema is really at version N-1, then `make db/migrations/force version=N-1` (or `-1` if N=1) and restart |
| Rollback locally | `make db/migrations/down` / `refresh` (wipes all data; refused for non-localhost DBs without `--allow-remote`) |
| Rollback in production | write a forward migration that reverses the change; `down` in production drops the `authula` schema = all users & sessions |
| Heavy migrations (large indexes) | `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block, and multiple statements in one file run as a single implicit transaction — put it as the **only statement** in its own migration file |
| Container | `docker run --env-file .env --entrypoint /app/migrate <image> up` |

Audit check: `python3 <plugin-root>/skills/layers/scripts/audit_layers.py` validates up/down pairs and duplicate numbers.

## 4. Secret rotation

- `APP_SECRET`: rotating it = every access token (JWT HS256) is immediately invalid;
  clients must refresh/sign in again. At least 32 characters (`openssl rand -base64 32`).
- `SUPER_USER`: change the password in env + `SEED_ON_BOOT=true` → the next boot
  resets the password and ends all of that account's sessions.
- `RESEND_API_KEY`, `GOOGLE_CLIENT_SECRET`, `SENTRY_DSN`: change the env, restart.
- DB password: change it in PostgreSQL first, then `DB_DSN`, restart all replicas.

## 5. Scaling out (more than one replica)

Run `grep -rn 'ponytail:' --include='*.go' .` — each marker is a
deliberate limitation:
- in-memory per-replica rate limiter → `limiter.Config{Storage: <redis>}`;
- in-memory idempotency cache + lock → shared storage (Redis) in
  `middlewares.Idempotency`;
- users mirror is only reconciled at boot → a DB trigger if drift becomes a problem.
`DB_MAX_OPEN_CONNS` is a **per-replica** budget (split in half with Authula);
total connections = replicas × that value, which must be < PostgreSQL's `max_connections`.

## 6. Release

Built-in flow (release-it + GitHub Actions):
1. Actions → **Release Prepare** (`auto` increment from conventional commits)
   → opens a `chore: release vX.Y.Z` PR after vet + test (+integration) + govulncheck.
2. Merge the PR → **Release Publish** creates the tag + GitHub release.
3. **Release** builds the multi-arch image → `ghcr.io/<owner>/<repo>:vX.Y.Z`, `vX.Y`, `latest`.
Requirement: the repo setting "Allow GitHub Actions to create and approve pull requests".
Commits must be conventional (`feat:`, `fix:`, `chore:`, `feat!:` for breaking changes).

## 7. Quick diagnosis (fatal messages at boot)

| Message | Cause |
|---|---|
| `flag app-secret must be at least 32 characters` | `APP_SECRET` empty/too short |
| `env AUTHULA_DATABASE_URL must not be set` | remove that variable; Authula uses `DB_DSN` |
| `flag debug must not be enabled in production` | `DEBUG=true` with `ENV` empty/production |
| `flag email-from / resend-api-key must be provided` | set `FROM_ADDRESS`, `RESEND_API_KEY` |
| `flag cors-allowed-origins: ... must be an origin` | remove the path/`*`; e.g. `https://app.example.com` |
| `flag trusted-proxies: ... is not an IP address or CIDR` | malformed IP/CIDR |
| `function uuidv7() does not exist` | PostgreSQL < 18 |
| 429s show up quickly during local testing | `ENV` is not `development`, so loopback is rate limited too (120/min API, 30/min auth) |
| 403 `cross-origin request refused` | the browser origin is not in `CORS_ALLOWED_ORIGINS` yet |
