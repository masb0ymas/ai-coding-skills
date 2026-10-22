# vine deploy reference

## Cloudflare Workers (vinext-cf)

`cloudflare.config.ts` is the deployment source of truth (Cloudflare Vite
plugin v2 + the `cf` CLI):

```ts
defineWorker({
  name: 'shop-web',                       // Worker name = default *.workers.dev subdomain
  entrypoint: 'vinext/server/fetch-handler',
  compatibilityDate: '2026-10-22',        // bump deliberately (vine:maintenance)
  compatibilityFlags: ['nodejs_compat'],
  assets: { /* static files: _next/static served directly, the rest hits the Worker */ },
  env: { ASSETS: bindings.assets(), IMAGES: bindings.images() },
  domains: ['app.example.com'],           // custom domain on a zone in the same account
})
```

- Auth: `cf auth login` (OAuth, local) or `CLOUDFLARE_API_TOKEN` (CI). A token
  that can reach several accounts needs `accountId` in `defineConfig({ ... })`.
  Token permissions: Workers Scripts Edit (+ Workers Routes / zone access for
  `domains`, Images for the `IMAGES` binding).
- `pnpm run deploy` = `vinext-cloudflare deploy`: builds, then uploads the
  entry Worker. `pnpm start` = `vite preview` in local workerd for a prod-like check.
- `/api` on Cloudflare: `next.config.ts` rewrites `/api/*` to
  `API_PROXY_TARGET`, read at **build** time. Set it in the shell / workflow
  variables before `pnpm run deploy`: unset locally ships the
  `http://localhost:8080` default, and in GitHub Actions an unset variable is
  `""`, so the generated workflow refuses to deploy without it. Alternative: `NEXT_PUBLIC_API_URL` = the
  API origin (needs CORS for that origin + the `Authorization` header).
- Caching/ISR (`kvDataAdapter`, Workers Cache, Response Store) are opt-in
  `@vinext/cloudflare` adapters; this app is session-driven and client-fetched, so
  leave them off unless there are public pages to cache.

## Docker — vinext (Node standalone)

- `output: 'standalone'` → `vite build` emits `dist/standalone/` (server.js +
  dist + pruned node_modules); the runtime stage copies only that.
- Runtime env: `PORT` (3000), `HOST` (0.0.0.0) — vinext reads `HOST`, not `HOSTNAME`.
- Build args: `API_PROXY_TARGET` (the rewrite target, e.g. `http://api:8080`
  in compose), `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`.

```sh
docker build --build-arg API_PROXY_TARGET=http://api:8080 -t web .
```

## Docker — vite SPA (nginx)

- `deploy/nginx/default.conf.template` is rendered by the nginx image at start
  (`envsubst` of `${API_UPSTREAM}` only). Routes: `/api/` → API, `/assets/`
  immutable cache, everything else → `index.html` with `no-cache`
  (TanStack Router handles the path client side).
- `API_UPSTREAM` must resolve when nginx starts, or the container exits.
- `X-Forwarded-For` is set to `$remote_addr` (replaced, not appended); behind
  another load balancer enable `real_ip` so the API rate limits per client.
- Same-origin `/api` → leave `VITE_API_URL` empty at build.

## Compose next to the API

```yaml
services:
  api:
    image: ghcr.io/acme/shop-api:latest   # e.g. a gofi API (gofi:deploy)
    env_file: .env.api
  web:
    build:
      context: .                          # workspace: the root, plus dockerfile: apps/web/Dockerfile
      args:
        API_PROXY_TARGET: http://api:8080 # vinext; vite uses API_UPSTREAM at runtime instead
    environment:
      API_UPSTREAM: http://api:8080       # vite/nginx only
    ports:
      - "3000:3000"                       # vite/nginx: "3000:8080"
    depends_on:
      - api
```

The gofi API expects `/v1`; vine calls `/api/v1`. Put the API behind a prefix
that matches (rewrite `/api` away in the proxy, or mount the API under `/api`)
— decide once and keep the frontend paths unchanged.

## Checklist

- [ ] `pnpm-lock.yaml` committed; `pnpm install --frozen-lockfile` works.
- [ ] `/sign-in` returns 200 HTML; a deep link (`/master/organization`) loads after refresh.
- [ ] `/api/v1/health` (or any API route) reaches the backend through the deployed origin.
- [ ] Sign in, list, create, edit, delete on the reference module; token refresh after expiry.
- [ ] Hashed assets: `Cache-Control: immutable`; HTML: `no-cache` (nginx) / revalidated (Workers).
- [ ] Container healthy (`docker inspect --format '{{.State.Health.Status}}'`), runs as non-root.
- [ ] No secret in build args or `.env.example`; `.env*` excluded by `.dockerignore`.
