---
name: scaffold
description: Scaffold a new React frontend with the masb0ymas/vine structure — vinext (Next.js App Router on Vite) for Cloudflare Workers, vinext as a Docker/Node server, or a Vite SPA with TanStack Router — with shadcn/ui, TanStack Query/Form/Table, axios, zod, and cookie-token auth against a /api/v1 backend. Use to create/bootstrap/generate a new frontend, admin panel or dashboard app, or to add a new app to a pnpm monorepo.
---

# vine:scaffold — generate a frontend app

Creates a new app from one of the three apps in
[masb0ymas/vine](https://github.com/masb0ymas/vine/tree/main/apps). All three
share the same layers (`lib/api` models → dtos → services → queries,
`components/block`, `components/ui`) and differ only at the framework seams.

Other skills in the vine plugin:

- `vine:layers` — add resources, pages, API calls and components inside the layers.
- `vine:maintenance` — health check, upgrades, env, auth/session problems.
- `vine:deploy` — Cloudflare Workers, Docker (Node standalone), nginx SPA image.

## Workflow

1. **Pick the variant.** Ask only if the user's target runtime is unclear:

   | `--variant` | Upstream app | Runtime | Choose when |
   |---|---|---|---|
   | `vinext-cf` | `apps/vinext-cf` | Cloudflare Workers (SSR) | hosting on Cloudflare, edge, no servers to run |
   | `vinext-docker` | `apps/vinext-web` | Node standalone server in Docker | self-hosted / Kubernetes / VPS, SSR needed |
   | `vite` | `apps/vite-web` | static files (nginx image) | pure SPA, no SSR, simplest hosting, or served next to the API |

2. **Run the generator** (Python stdlib + git):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/scaffold/scripts/scaffold.py --dest ./shop-web --variant vinext-cf
   ```
   Options: `--name` (package / Worker name; default = folder name), `--title`
   (display name), `--ref` (vine git ref; default = the commit these skills
   document, `--ref main` for the latest), `--from <local vine checkout>` (offline),
   `--no-git-init`, `--force`.
   The script copies the app, renames it (package.json, `<title>`/metadata,
   Worker name), writes `.env.example` and a README, and:
   - **standalone** (no parent `pnpm-workspace.yaml` with `packages:`): adds
     `packageManager` and a settings-only `pnpm-workspace.yaml` carrying
     `allowBuilds` (esbuild, workerd, lightningcss, sharp need their install scripts), then `git init`.
   - **inside a pnpm workspace** (e.g. `--dest apps/admin`): becomes one more package.
   - `vinext-docker`: also runs `vine:deploy`'s `apply_deploy.py --target docker`
     (Dockerfile matching the layout + `output: 'standalone'`).
3. **Verify** — the step is done when all three commands pass:
   ```sh
   pnpm install
   pnpm exec tsc --noEmit
   pnpm build
   ```
4. **Report**: location, variant, name, next commands (`pnpm dev`; the app
   proxies `/api` to `http://localhost:8080`), and which deploy path fits
   (`vine:deploy`).

## Generated structure

Layer contracts, the vinext vs vite differences, and the starter features are in
`references/structure.md`. Read it before changing anything framework-specific.
New features follow `vine:layers`; keep the layout as generated.

## Rules

- Keep the upstream versions at scaffold time; upgrades (including the exact
  `vite` pin in `vinext-cf`) go through `vine:maintenance`.
- Secrets never go in `NEXT_PUBLIC_*` / `VITE_*`: those are inlined into the
  browser bundle. This frontend holds no server secrets.
- If GitHub is unreachable, use `--from` with a local clone of masb0ymas/vine.
