---
name: deploy
description: Deploy a vine-style React frontend — vinext to Cloudflare Workers (cloudflare.config.ts, cf auth, GitHub Actions), vinext as a Node standalone Docker image, or a Vite + TanStack Router SPA in an nginx image that proxies /api to the backend. Covers Dockerfiles for standalone apps and pnpm monorepos, build-time env, healthchecks, docker compose next to the API, custom domains. Use for "deploy", "docker", "container", "cloudflare", "workers", "nginx", "CI deploy".
---

# vine:deploy — Cloudflare, Docker, nginx

The target follows the variant; detect it from the app (`cloudflare.config.ts`
→ vinext-cf, `vinext` dependency → vinext, `@tanstack/react-router` → vite):

| App | Target | Output |
|---|---|---|
| vinext-cf | Cloudflare Workers | `pnpm run deploy` (`vinext-cloudflare deploy`) builds and uploads the Worker |
| vinext (docker) | Node image | `dist/standalone/server.js` on `node:24-alpine`, port 3000 |
| vite | nginx image | `dist/` on nginx-unprivileged, port 8080, `/api` proxied to `API_UPSTREAM` |

A vinext-cf app that should run in Docker instead: scaffold the `vinext-docker`
variant and move `components/`/`lib/` over (they are identical).

## Workflow

1. **Check the app**: package.json + lockfile present, `health.sh --quick`
   (`vine:maintenance`) green, and where the API lives in production (same
   origin through the proxy, or another origin → `*_API_URL`).
2. **Apply** (Python stdlib, idempotent; a replaced file is kept as `.bak`):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/deploy/scripts/apply_deploy.py --root . --target docker
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/deploy/scripts/apply_deploy.py --root . --target cloudflare [--branch main]
   ```
   - `docker`, vinext: `Dockerfile` (+ `output: 'standalone'` in `next.config.ts`).
     vite: `Dockerfile` + `deploy/nginx/default.conf.template`. Both write
     `.dockerignore` when missing. Inside a pnpm workspace the Dockerfile builds
     from the workspace root with `pnpm --filter <name>...`.
   - `cloudflare` (vinext-cf only): `.github/workflows/deploy-<name>.yml` at the
     git root, deploying on push to `--branch` with `CLOUDFLARE_API_TOKEN`.
3. **Configure** per target — details and the full checklist in
   `references/deploy.md`:
   - Cloudflare: Worker name / `domains` / bindings in `cloudflare.config.ts`;
     `cf auth login` locally or `CLOUDFLARE_API_TOKEN` in CI.
   - Build-time env (`API_PROXY_TARGET`, `NEXT_PUBLIC_*`, `VITE_*`) as
     `--build-arg` / workflow variables; runtime env only `PORT`, `HOST`
     (vinext) or `API_UPSTREAM` (nginx).
4. **Verify** — done when the target answers with the app:
   ```sh
   # Cloudflare
   pnpm build && pnpm start                    # local workerd preview, then
   pnpm run deploy && curl -I https://<worker-url>/sign-in
   # Docker
   docker build -t web .                       # workspace: -f apps/<app>/Dockerfile from the root
   docker run --rm -p 3000:3000 web            # vite: -p 3000:8080 -e API_UPSTREAM=http://host.docker.internal:8080
   curl -I localhost:3000/sign-in              # 200 + HTML; /api/v1/... reaches the backend
   ```
   Then walk the checklist in `references/deploy.md`.

## Rules

- No secrets in build args: `NEXT_PUBLIC_*` / `VITE_*` end up in public JS.
- Images run as non-root (`USER node`, nginx-unprivileged) and carry a `HEALTHCHECK`.
- Changing a build-time variable means a new build, never just a restart.
