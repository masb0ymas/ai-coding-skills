---
name: deploy
description: Containerize and deploy a gofi-style Go API (Fiber v3 + PostgreSQL) as a backend server image, optionally serving a single-page app (React/Vue/Svelte/Vite) from the same Go backend or from a separate nginx server image. Covers Dockerfiles (distroless, multi-arch), healthcheck, docker compose with migrations, SPA fallback routing and caching, reverse proxy, env for production. Use for "deploy", "docker", "container", "run the SPA on the backend", "serve the frontend from Go", "server image".
---

# gofi:deploy — backend container & SPA

Three modes; pick based on the user's needs (ask if it is unclear whether there is an SPA):

| Mode | Result | When |
|---|---|---|
| `api` | 1 image: API + migrate + healthcheck | backend only / SPA hosted elsewhere |
| `embedded` | 1 image: the API also serves the SPA at `/` | simplest deploy, one origin, one container |
| `separate` | API image + nginx SPA image that proxies `/v1` & `/health` | SPA & API scaled/released separately, CDN-friendly |

## Workflow

1. **Check the project**: confirm the gofi structure (`go.mod`, `cmd/api`). For SPA
   modes, find the frontend project folder (default `web/`, output `dist/`; Vite →
   `dist`, CRA → `build`). If it does not exist, ask the user to add it or set
   `--web-dir`/`--web-out`.
2. **Apply** (Python stdlib, idempotent, replaced files are saved as `.bak`):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/deploy/scripts/apply_deploy.py --root . --mode embedded \
     --web-dir web --web-out dist --compose
   ```
   - all modes: `cmd/healthcheck` (a probe for the shell-less distroless image),
     `Dockerfile` + `HEALTHCHECK`, `.dockerignore`, optional `docker-compose.yml`
     (postgres:18 → `migrate up` job → api [+ web]).
   - `embedded`: `internal/middlewares/spa.go` + test, `SPA_DIR` in config/flag/
     `.env.example`, SPA mounted after routes in `server.go`, the JSON `/` route
     only active without an SPA, helmet COEP relaxed for CDN assets.
   - `separate`: `Dockerfile.web` + `deploy/nginx/default.conf.template`.
3. **Verify**:
   ```sh
   gofmt -l . && go build ./... && go test ./...      # TestSPA runs too
   docker build -t app .                               # + -f Dockerfile.web for separate
   docker compose up -d --build                        # --profile web for separate
   curl -i localhost:8080/health
   ```
   Then run the checklist in `references/deploy.md` (SPA route → HTML no-cache,
   `/v1/xxx` → JSON 404, `/assets/*` immutable, container `healthy`).
4. **Report**: mode, changed files (and `.bak`s), required production env,
   and the image release steps.

## Key rules

- One origin for the browser (embedded/separate) → no CORS, first-party session
  cookies, the CSRF guard keeps working. The SPA calls `/v1/...` relatively.
- The SPA is always mounted **after** the API routes and never answers `/v1`,
  `/health`, methods other than GET/HEAD, or missing files with an extension.
- `index.html` is `no-cache`; hashed assets are `immutable` for a year.
- The runtime image stays distroless nonroot with no shell: the healthcheck uses
  `/app/healthcheck` (exec form), migrations use `--entrypoint /app/migrate`.
- Never bake `.env` into the image; secrets come through runtime env.
- Behind a proxy/LB/nginx: set `TRUSTED_PROXIES`, `AUTH_BASE_URL` = public origin.
- More than one replica: run migrations as a separate job (`MIGRATE_ON_BOOT=false`),
  and read the `ponytail:` markers (rate limit & idempotency are still in-memory).

Topology details, the SPA-embedded-in-the-binary variant (`go:embed`), CSP, production
env, Kubernetes/Cloud Run, and releasing the second image: `references/deploy.md`.
