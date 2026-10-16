# Deploying gofi — details

## Topology

```
A. api        browser/client ──► [API image :8080]  /v1, /health, /static
B. embedded   browser ──► [API image :8080]  /v1 → API · SPA files · anything else → index.html
C. separate   browser ──► [nginx SPA :8080] ─ /v1, /health ─► [API image :8080]
                               └─ SPA files, fallback index.html
```
Every variant makes the browser see **one origin**, so Authula's session cookie
stays first-party, CORS is unnecessary, and the CSRF protection (`Sec-Fetch-Site`)
treats requests as `same-origin`. The SPA calls the API with relative URLs
(`fetch("/v1/categories")`; `credentials: "include"` is not needed for same-origin).

If the SPA is hosted on another origin (e.g. Vercel/Netlify), that is the `api` variant:
set `CORS_ALLOWED_ORIGINS` to the SPA origin, use bearer tokens, and be aware that
the session cookie becomes cross-site (SameSite=Lax is not sent on cross-site fetches).

## Code changes for embedded mode (what `apply_deploy.py` does)

1. `internal/middlewares/spa.go` (+ `spa_test.go`): `SPA(SPAConfig{FS, Exclude, AssetsPrefix})`.
   - GET/HEAD only; prefixes in `Exclude` are always passed through to the API (JSON 404, not HTML).
   - File exists → served; `/assets/*` gets `Cache-Control: public, max-age=31536000, immutable`, everything else `no-cache`.
   - Missing path without an extension → `index.html` (`no-cache`).
   - Missing path with an extension → 404 (stale bundles are not answered with HTML).
   - Fails to start if `index.html` is missing (caught early at deploy time).
2. `internal/config/config.go`: `ConfigApp.SPADir`.
3. `cmd/api/flag.go`: flag `spa-dir` ← env `SPA_DIR` (empty = disabled).
4. `cmd/api/server.go`: `server.Use(spa)` **after** `routes(server, app)`;
   helmet `CrossOriginEmbedderPolicy: "unsafe-none"` so CDN assets are not blocked.
5. `cmd/api/routes.go`: the JSON `GET /` route is only active when `SPADir` is empty.
6. `.env.example`: `SPA_DIR=`.

If the automatic patch fails (the code has already been changed), apply points 2–6
by hand following the snippets above; no other changes are needed.

### Variant: SPA embedded in the binary

For a single binary without a folder:
```go
// web/embed.go  (package at the root, like migrations/)
package web

import (
	"embed"
	"io/fs"
)

//go:embed all:dist
var dist embed.FS

// FS returns the built SPA rooted at dist/.
func FS() (fs.FS, error) { return fs.Sub(dist, "dist") }
```
In `server.go` replace `os.DirFS(dir)` with `web.FS()`. Consequences: `web/dist`
must exist before `go build` (build the SPA in a Node stage, then copy it to
`/src/web/dist` before the Go stage compiles), and a local `go build` fails
without an SPA build. That is why the skill defaults to a folder (`SPA_DIR`).

### Content-Security-Policy

Helmet does not set a CSP by default. For an SPA, add one when ready:
`helmet.Config{ContentSecurityPolicy: "default-src 'self'; img-src 'self' data: https:; connect-src 'self'"}`
and test it in the browser (inline scripts/analytics need exceptions).

## Separate mode (nginx)

- `Dockerfile.web` builds the SPA, then uses `nginxinc/nginx-unprivileged`
  (port 8080, non-root). `deploy/nginx/default.conf.template` is rendered at start
  with `API_UPSTREAM` (default `http://api:8080`).
- The API must trust nginx: `TRUSTED_PROXIES=<container network subnet>`;
  without it the rate limiter counts every user as one IP (nginx).
- `AUTH_BASE_URL` = the public origin (the nginx domain), because email links and
  the Google callback are opened by the browser.
- Release: the built-in workflow only builds `Dockerfile`. Add a second job to
  `release.yml` with `file: Dockerfile.web` and the image name `${{ github.repository }}-web`.

## Production environment (minimum)

```
ENV=production
APP_SECRET=<≥32 characters>
DB_DSN=postgres://user:pass@host:5432/db?sslmode=require
AUTH_BASE_URL=https://app.example.com
FROM_ADDRESS=noreply@example.com
RESEND_API_KEY=...
TRUSTED_PROXIES=<load balancer / nginx IP/CIDR>
MIGRATE_ON_BOOT=false        # migrate via a separate job when >1 replica
SEED_ON_BOOT=true            # once to create the super user, then may be false
SUPER_USER=admin@example.com:<12–128 characters>
SPA_DIR=/app/web             # already set by the fullstack image
```
TLS is terminated at the reverse proxy/LB; the session cookie is `Secure` outside `development`,
so access it over HTTPS (http://localhost is still accepted by browsers).

## Target platforms

| Platform | Notes |
|---|---|
| VM + compose | `docker compose up -d --build`; put Caddy/Traefik/nginx TLS in front; back up the `pgdata` volume |
| Kubernetes | API Deployment (`readinessProbe`/`livenessProbe` HTTP `GET /health` port 8080), a `migrate up` Job before rollout, a Secret for env; >1 replica → see the `ponytail:` markers (in-memory rate limit & idempotency) |
| Cloud Run / Fly.io / Railway | reads `PORT` (already supported); `MIGRATE_ON_BOOT=true` is enough for 1 instance; set `TRUSTED_PROXIES` to the platform's proxy range |
| Image registry | the built-in `release.yml` workflow pushes multi-arch images to `ghcr.io/<owner>/<repo>` |

## Go-live checklist

- [ ] `go test ./...` is green (including `TestSPA` when embedded) and the integration test with `TEST_DB_DSN`.
- [ ] `docker build` succeeds; `docker run --env-file .env -p 8080:8080 <image>` then `curl -i localhost:8080/health` → 200.
- [ ] SPA modes: `curl -i localhost:8080/some/route` → HTML `no-cache`; `curl -i localhost:8080/v1/nope` → JSON 404; `/assets/*` → `immutable`.
- [ ] `docker inspect --format '{{.State.Health.Status}}' <container>` → `healthy`.
- [ ] No `.env` in the image (`.dockerignore`), `DEBUG=false`, `ENV=production`.
