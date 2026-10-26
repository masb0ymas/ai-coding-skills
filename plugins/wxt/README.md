# wxt plugin

A Claude Code plugin with five skills for building browser extensions with
[WXT](https://wxt.dev), the Vite-based web extension framework: file-based
entrypoints, a generated manifest, MV2/MV3 builds for Chrome, Firefox, Edge,
and Safari, and store submission from the CLI.

The skills follow WXT 0.21 and wrap its own CLI (`wxt init`, `wxt`,
`wxt build`, `wxt zip`, `wxt prepare`, `wxt submit`) instead of replacing it.

| Skill | For | Script |
|---|---|---|
| `/wxt:scaffold` (main) | new extension from the vanilla/React/Vue/Svelte/Solid template, or WXT in an existing project | — (`wxt init`) |
| `/wxt:entrypoints` | background, content scripts and their UIs, popup/options/side panel, storage, messaging, manifest, env | `scripts/audit_entrypoints.py` |
| `/wxt:maintenance` | health check, WXT upgrades, dev-mode and debugging, Vitest/Playwright | `scripts/health.sh` |
| `/wxt:publish` | ZIPs, Firefox sources, `wxt submit` to Chrome/Firefox/Edge, GitHub Actions release | `assets/release.yml` |
| `/wxt:migrate` | move an existing extension (Plasmo, CRXJS, vite-plugin-web-extension, webpack, plain manifest) to WXT without changing its permissions | `scripts/compare_manifests.py` |

Claude picks the right skill from the request, so the slash command is optional.

## Install

```sh
claude plugin marketplace add masb0ymas/ai-coding-skills
claude plugin install wxt@ai-coding-skills
```

From a local clone, without installing:

```sh
claude --plugin-dir ./plugins/wxt
```

The scripts need Python 3.10+ (stdlib only) and `bash`; the projects need
Node 22+ and a package manager (pnpm, npm, yarn, or bun). `health.sh` uses
`skills/entrypoints/scripts/audit_entrypoints.py` from the same plugin, and so
does the `migrate` workflow.

## Update

Refresh the marketplace catalog, then update the plugin and restart Claude Code
to load the new version:

```sh
claude plugin marketplace update ai-coding-skills
claude plugin update wxt@ai-coding-skills
```

Inside a session, `/plugin` opens the same marketplace and plugin management.
With `--plugin-dir`, `git pull` in the clone is the update.

Maintainers: bump `version` in `.claude-plugin/plugin.json` with every
release, since installed copies are cached by version and an unchanged version
is not picked up by `claude plugin update`.

## Example prompts

```text
/wxt:scaffold create a React extension in ./tab-notes
"Add a side panel that lists the open tabs and a setting to hide pinned ones"
"Inject a floating button on github.com pull request pages, styled with Tailwind"
"Upgrade WXT to the latest version and check the extension still builds"
"Set up a GitHub Action that submits to the Chrome Web Store and Firefox"
/wxt:migrate convert this Plasmo extension to WXT, keep the same permissions
```
