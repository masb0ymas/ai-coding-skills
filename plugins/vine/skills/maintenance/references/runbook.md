# vine maintenance runbook

`<plugin-root>` = `${CLAUDE_PLUGIN_ROOT}`. Run `health.sh` before and after each task.

## 1. Upgrading dependencies

1. `pnpm outdated` to see the gap; `pnpm update` takes everything within the
   ranges in package.json (patch/minor) — do that first and commit alone.
2. Then one **family** per commit; each family moves together because its
   packages are released against each other:

   | Family | Packages | Notes |
   |---|---|---|
   | vinext | `vinext`, `@vinext/cloudflare`, `@cloudflare/vite-plugin`, `cf`, `vite`, `@vitejs/plugin-rsc`, `@vitejs/plugin-react` | `vinext-cf` pins `vite` exactly (8.3.0 upstream, inside advisory GHSA-587h-7wmj-h5pm, fixed in 8.3.3); move the pin together with `@cloudflare/vite-plugin` and confirm `pnpm build && pnpm start` in workerd. Read the vinext changelog for `next/*` API gaps closed or changed. |
   | React | `react`, `react-dom`, `react-server-dom-webpack`, `@types/react*` | keep `react-server-dom-webpack` on the same version as `react` in vinext apps (RSC wire format). |
   | TanStack Router | `@tanstack/react-router`, `@tanstack/router-plugin`, `@tanstack/react-router-devtools`, `@tanstack/router-cli`, `@tanstack/devtools-vite`, `@tanstack/react-devtools` | pinned exactly in vite apps (`router-cli` uses a caret range); bump together, then `pnpm generate-routes` and commit `routeTree.gen.ts`. |
   | TanStack data | `@tanstack/react-query(-devtools)`, `@tanstack/react-form`, `@tanstack/react-table` | react-table v9 typing (`AppColumnDef`, `features` in `react-table.tsx`) breaks on majors. |
   | UI | `radix-ui`, `tailwindcss`, `@tailwindcss/*`, `lucide-react`, `@tabler/icons-react`, `sonner`, `next-themes` | check `components/ui` visually (sign-in, sidebar, table, dialog). |
   | Tooling | `typescript`, `@types/node` | vinext apps use TypeScript 7, the vite app TypeScript 6; keep each on its own line unless both are tested. |

3. Majors: read the migration guide (Context7 / the package changelog) before
   editing, upgrade, run `health.sh`, and click through sign-in → list →
   create → edit → delete on the reference module.
4. A failing `pnpm audit`: `pnpm why <pkg>` to find the path; prefer upgrading
   the direct dependency; use `pnpm.overrides` in package.json (or
   `overrides:` in pnpm-workspace.yaml) only for transitive fixes, with a
   comment saying when to remove it.

## 2. shadcn/ui components

`components.json` drives `pnpm dlx shadcn@latest add <name>`. Several files in
`components/ui` are local (data-grid*, input's `InputWrapper`/`inputVariants`,
select's `indicatorPosition`), so re-adding an existing component with
`--overwrite` drops those edits: diff before accepting.

## 3. Node and runtime versions

- Docker: the `node:24-alpine` tag in the Dockerfile (both stages) and
  `node-version` in CI move together.
- Cloudflare: bump `compatibilityDate` in `cloudflare.config.ts` deliberately
  (it opts into runtime behaviour changes), then `pnpm build && pnpm start`
  (local workerd) before deploying.
- pnpm: `packageManager` in the root package.json; CI and Docker read it via corepack / pnpm/action-setup.

## 4. Environment changes

`NEXT_PUBLIC_*`, `VITE_*` and `API_PROXY_TARGET` are fixed at build time:
changing one means rebuilding and redeploying, not restarting. Adding one
touches `config/env.ts` (+ `runtimeEnv` for vinext), `.env.example`, the
Dockerfile `ARG`s, and the Cloudflare workflow `env` — `check_env_sync.py`
fails until `.env.example` documents it.

## 5. Auth and session problems

| Symptom | Cause / fix |
|---|---|
| Redirect loop between `/sign-in` and `/dashboard` (vinext) | the server guard only checks cookie presence; a stale refresh cookie passes it, then the API 401s. `clearAuthTokens()` runs on refresh failure; check the refresh endpoint answers 401 (not 500) for a dead token. |
| Every request 401 after deploy | API on another origin without `NEXT_PUBLIC_API_URL`/`VITE_API_URL`, or the proxy target wrong at build time (§4). |
| CORS errors with a cross-origin API | tokens travel as an `Authorization` header, so the API must allow the frontend origin and that header; the same-origin `/api` proxy avoids CORS entirely. |
| Parallel requests each refresh | they should share the single in-flight `refreshing` promise in `client-fetch.ts`; keep that when editing the interceptor. |

Tokens live in non-httpOnly cookies (readable by JS, so the axios interceptor
can send them): treat any XSS as session theft, keep `dangerouslySetInnerHTML`
out of user content, and keep access tokens short-lived on the API.

## 6. API contract drift

`types/api.ts` mirrors the backend envelope (`data`, `metadata`, `message`,
`errors[]`). When the backend changes it, update `types/api.ts` and
`axios-error.ts` together; models in `lib/api/models` follow the JSON field
names (snake_case) exactly.

## 7. Safe refactoring

- Keep behaviour changes and structural moves in separate commits.
- Keep the layer contracts of `vine:layers`; `audit_layers.py` must stay green.
- Keep comments that explain why (refresh single-flight, action cell never
  swapped for a skeleton, partial form state); update them when behaviour changes.
