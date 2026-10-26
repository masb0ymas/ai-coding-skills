---
name: scaffold
description: Scaffold a new browser extension with WXT (wxt.dev) — `wxt init` with the vanilla, React, Vue, Svelte, or Solid template, or a from-scratch WXT setup. Use to create/bootstrap/start a Chrome, Firefox, Edge, or Safari extension, a web extension, an MV3 extension, or a new WXT project. Existing extensions → wxt:migrate.
---

# wxt:scaffold — start a WXT extension

WXT builds extensions from files in `entrypoints/`; there is no hand-written
`manifest.json`. The official templates are the starting point.

Other skills in the wxt plugin:

- `wxt:entrypoints` — add popup, background, content scripts, UIs, storage, messaging.
- `wxt:maintenance` — health check, upgrades, debugging, tests.
- `wxt:publish` — zip, submit to Chrome / Firefox / Edge stores, CI release.
- `wxt:migrate` — move an existing extension (Plasmo, CRXJS, webpack, plain manifest) to WXT.

## Workflow

1. **Pick the template and package manager.** Ask only if the request doesn't say:

   | `-t` | Brings | Module in `wxt.config.ts` |
   |---|---|---|
   | `vanilla` | TypeScript, no UI framework | — |
   | `react` | React 19 popup | `@wxt-dev/module-react` |
   | `vue` | Vue popup | `@wxt-dev/module-vue` |
   | `svelte` | Svelte popup | `@wxt-dev/module-svelte` |
   | `solid` | Solid popup | `@wxt-dev/module-solid` |

   `--pm` is `pnpm`, `npm`, `yarn`, or `bun`. Default to pnpm when unstated.

2. **Generate** (non-interactive when directory, `-t`, and `--pm` are all given):
   ```sh
   pnpm dlx wxt@latest init my-ext -t react --pm pnpm < /dev/null
   cd my-ext && git init      # init doesn't create the repo when stdin is closed
   ```
   - The directory must be empty or missing; init aborts otherwise.
   - Don't pass `--no-git`: wxt 0.21.4 rejects it (`Unknown option --git`).
   - Needs network (templates come from GitHub). Offline → step 2b.
   - `vite` is a required peer, but the framework templates (React in
     0.21.4) don't list it. Yarn doesn't auto-install peers, so add it
     explicitly: `pnpm add -D vite`.

   **2b. From scratch without a template**: `pnpm add -D wxt vite web-ext`,
   add the scripts below, `tsconfig.json` with
   `{ "extends": "./.wxt/tsconfig.json" }`, and a first entrypoint
   (`entrypoints/background.ts`) per `wxt:entrypoints`. An extension that
   already exists (Plasmo, CRXJS, webpack, plain manifest) → `wxt:migrate`.

3. **Set the identity**: `name`, `description`, `version` in `package.json` feed
   the manifest (`version: "1.2.0-beta1"` → `version 1.2.0`, `version_name`
   as written). Icons: `public/icon/{16,32,48,96,128}.png` are picked up
   automatically. Permissions go in `wxt.config.ts`:
   ```ts
   export default defineConfig({
     modules: ['@wxt-dev/module-react'],
     manifest: { permissions: ['storage'] },
   });
   ```

4. **Verify** — done when all pass:
   ```sh
   pnpm install          # postinstall runs `wxt prepare` → .wxt/ types + auto-imports
   pnpm compile          # tsc --noEmit
   pnpm build            # .output/chrome-mv3/
   pnpm build:firefox    # .output/firefox-mv2/
   ```

5. **Report**: location, template, `pnpm dev` (opens Chrome with the extension
   when `web-ext` is installed; `pnpm dev:firefox` for Firefox), where to load
   it by hand (`chrome://extensions` → Load unpacked → `.output/chrome-mv3`),
   and the next skill (`wxt:entrypoints` for features, `wxt:publish` to ship).

## Template scripts

```json
{
  "dev": "wxt", "dev:firefox": "wxt -b firefox",
  "build": "wxt build", "build:firefox": "wxt build -b firefox",
  "zip": "wxt zip", "zip:firefox": "wxt zip -b firefox",
  "compile": "tsc --noEmit", "postinstall": "wxt prepare"
}
```

## Rules

- Requires Node ≥ 22, Vite ≥ 6.3.4, TypeScript ≥ 5.4 (wxt 0.21).
- Keep `.output/`, `.wxt/`, `web-ext.config.ts`, `stats.html` and `stats-*.json` in `.gitignore`
  (the templates already do).
- Optional layout: `srcDir: 'src'` in `wxt.config.ts` moves `entrypoints/`,
  `components/`, `utils/`, `hooks/`, `assets/` and `app.config.ts` under `src/`;
  `public/` and `modules/` stay at the root. Decide at scaffold time.
- Don't hand-write `manifest.json`; it is generated into `.output/<target>/`.
