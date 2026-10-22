# vine plugin

A Claude Code plugin with four skills for building and maintaining React
frontends structured like [masb0ymas/vine](https://github.com/masb0ymas/vine/tree/main/apps):

- **vinext-cf**: vinext (Next.js App Router on Vite) on Cloudflare Workers
- **vinext-docker**: vinext as a Node standalone server in Docker
- **vite**: Vite SPA with TanStack Router, served by nginx

All three share shadcn/ui, TanStack Query/Form/Table, axios, zod, nuqs, and
cookie-token auth against a `/api/v1` backend. The scaffold fetches the apps
from GitHub at a pinned commit (`953fa11`), or from a local clone with `--from`.

| Skill | For | Script |
|---|---|---|
| `/vine:scaffold` (main) | generate a new app (standalone or inside a pnpm workspace) | `scripts/scaffold.py` |
| `/vine:layers` | add resources, API calls, components, routes, and menus within the models/dtos/services/queries/components layers | `scripts/new_resource.py`, `scripts/audit_layers.py` |
| `/vine:maintenance` | health check, upgrades, env, auth/session issues, CI | `scripts/health.sh`, `scripts/check_env_sync.py`, `assets/ci.yml` |
| `/vine:deploy` | Cloudflare Workers, Node standalone image, nginx SPA image | `scripts/apply_deploy.py` |

Claude picks the right skill from the request, so the slash command is optional.

## Install

```sh
claude plugin marketplace add masb0ymas/ai-coding-skills
claude plugin install vine@ai-coding-skills
```

From a local clone, without installing:

```sh
claude --plugin-dir ./plugins/vine
```

The scripts need Python 3.10+ (stdlib only), `bash`, `git`, Node 24, and pnpm
(the version in vine's `packageManager`, via corepack). `health.sh` uses
`skills/layers/scripts/audit_layers.py` from the same plugin, and the scaffold's
`vinext-docker` variant calls `skills/deploy/scripts/apply_deploy.py`.

## Update

Refresh the marketplace catalog, then update the plugin and restart Claude Code
to load the new version:

```sh
claude plugin marketplace update ai-coding-skills
claude plugin update vine@ai-coding-skills
```

Inside a session, `/plugin` opens the same marketplace and plugin management.
With `--plugin-dir`, `git pull` in the clone is the update.

Maintainers: bump `version` in `.claude-plugin/plugin.json` with every
release, since installed copies are cached by version and an unchanged version
is not picked up by `claude plugin update`.

## Example prompts

```text
/vine:scaffold create an admin panel on Cloudflare in ./shop-admin
"Add a product page: name, price (int), category_id (uuid), active (bool)"
"Check the health of this frontend and upgrade the TanStack Router packages"
"Dockerize this vite app so nginx proxies /api to the API container"
```
