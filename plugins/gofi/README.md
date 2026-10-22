# gofi plugin

A Claude Code plugin with four skills for building and maintaining Go APIs structured like
[masb0ymas/gofi](https://github.com/masb0ymas/gofi) (Fiber v3, PostgreSQL 18,
golang-migrate, Authula). The template in `skills/scaffold/template` is a snapshot
of upstream `795c0c1` (MIT, copyright masb0ymas — see `template/LICENSE.md`).

| Skill | For | Script |
|---|---|---|
| `/gofi:scaffold` (main) | generate a new project with the gofi structure | `scripts/scaffold.py` |
| `/gofi:layers` | add features while staying inside the cmd/internal/app/config/dtos/lib/middlewares/models/handlers/repositories/seeders/migrations layers | `scripts/new_resource.py`, `scripts/audit_layers.py` |
| `/gofi:maintenance` | health check, upgrades, migrations, secrets, CI, releases | `scripts/health.sh`, `scripts/check_env_sync.py`, `assets/ci.yml` |
| `/gofi:deploy` | backend container, SPA served by Go, or SPA in an nginx image | `scripts/apply_deploy.py` + `assets/` |

Claude also picks the right skill on its own from the request, so the slash command is optional.

## Install

From GitHub (Claude Code):

```sh
claude plugin marketplace add masb0ymas/ai-coding-skills
claude plugin install gofi@ai-coding-skills
```

Inside a session, `/plugin marketplace add masb0ymas/ai-coding-skills` and
`/plugin install gofi@ai-coding-skills` do the same.

From a local clone, without installing:

```sh
claude --plugin-dir ./plugins/gofi
```

This is a Claude Code plugin, so `install.sh` does not copy it into the
`.agents`, `.openclaude`, or `.zcode` skill folders.

All scripts only need Python 3.10+ (stdlib), `bash`, `gofmt`/Go, and `git`.
`skills/maintenance/scripts/health.sh` runs `skills/layers/scripts/audit_layers.py`
from the same plugin.

## Update

Refresh the marketplace catalog, then update the plugin and restart Claude Code
to load the new version:

```sh
claude plugin marketplace update ai-coding-skills
claude plugin update gofi@ai-coding-skills
```

Inside a session, `/plugin` opens the same marketplace and plugin management.
With `--plugin-dir`, `git pull` in the clone is the update.

Maintainers: bump `version` in `.claude-plugin/plugin.json` with every
release, since installed copies are cached by version and an unchanged version
is not picked up by `claude plugin update`.

## Example prompts

```text
/gofi:scaffold create a new API project github.com/acme/shop
"Add a product resource: name, price, category_id referencing categories"
"Check the health of this codebase and upgrade patch dependencies"
"Set up Docker so the backend also serves the SPA in the web/ folder"
```
