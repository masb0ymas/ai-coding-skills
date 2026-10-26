---
name: entrypoints
description: Add or change features in a WXT browser extension — entrypoints (background, content scripts, popup, options, side panel, new tab, devtools, sandbox, unlisted pages/scripts/CSS), content script UIs (integrated, shadow root, iframe), main-world injection, storage (`storage.defineItem`), messaging, manifest permissions, env vars, per-browser and MV2/MV3 differences, i18n, WXT modules. Use for "add a popup/content script/side panel", "inject UI into a page", "save settings", "send a message to the background", or to audit entrypoint mistakes.
---

# wxt:entrypoints — where extension code goes

WXT turns every file in `<srcDir>/entrypoints/` into a bundle and derives the
manifest from it. The file **name** decides the type; options live **inside**
the file. No WXT project yet → `wxt:scaffold`.

## Entrypoint map

| File (or `<name>/index.*`) | Type | Output |
|---|---|---|
| `background.ts` | service worker (MV3) / background page (MV2) | `background.js` |
| `content.ts`, `<name>.content.ts(x)` | content script | `content-scripts/<name>.js` |
| `popup.html` | toolbar action popup | `popup.html` |
| `options.html` | options page | `options.html` |
| `sidepanel.html`, `<name>.sidepanel.html` | Chrome side panel / Firefox sidebar | `<name>.html` |
| `newtab.html`, `history.html`, `bookmarks.html` | browser page override | same |
| `devtools.html` | devtools page | `devtools.html` |
| `sandbox.html`, `<name>.sandbox.html` | sandboxed page (Chromium only) | `<name>.html` |
| `<name>.html` | unlisted page, open via `browser.runtime.getURL('/<name>.html')` | `<name>.html` |
| `<name>.ts` | unlisted script (`defineUnlistedScript`) | `<name>.js` |
| `<name>.css` / `<name>.content.css` | unlisted CSS | `<name>.css` / `content-scripts/<name>.css` |

Options per type (content script `matches`/`runAt`/`world`/`cssInjectionMode`/
`registration`, popup `<meta name="manifest.*">`, `include`/`exclude` per
browser) and copy-ready code: `references/recipes.md`.

## Workflow

1. **Locate the project**: read `wxt.config.ts` (`srcDir`, `entrypointsDir`,
   `modules`, `manifest`) and list the entrypoints dir.
2. **Pick the place** for the change:
   - extension-wide manifest fields (`permissions`, `host_permissions`,
     `web_accessible_resources`, `commands`, `default_locale`) → `manifest` in
     `wxt.config.ts`; use the function form `manifest: ({ browser, manifestVersion, mode }) => ({...})`
     when it differs per target or reads env.
   - entrypoint options → the entrypoint file.
   - shared code → `components/`, `utils/`, `hooks/` (React/Solid),
     `composables/` (Vue) — all auto-imported; never loose files in `entrypoints/`.
   - persistent state → `utils/storage.ts` with `storage.defineItem`.
   - build-time logic → a local module in `modules/` (auto-loaded).
3. **Write the code** with the recipes in `references/recipes.md`. A UI entrypoint
   with a framework is a folder: `popup/index.html` + `main.tsx` + `App.tsx` +
   `style.css`.
4. **Verify** — done when all pass:
   ```sh
   pnpm wxt prepare                     # regenerates auto-import types
   pnpm compile
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/entrypoints/scripts/audit_entrypoints.py --root .
   pnpm build && pnpm build:firefox
   ```
   Then read `.output/chrome-mv3/manifest.json` and confirm the new entry,
   permissions, and matches are what you expect. Content scripts are missing
   from the manifest **only in MV3 dev mode** (registered at runtime for HMR).

## Hard rules

- JS/TS entrypoints run in Node at build time to read their options: all
  runtime code (`browser.*`, `document`, `window`, listeners) goes **inside
  `main()`**. Top-level code also runs in Node during the build and fails
  with `... not implemented` for APIs the fake browser lacks.
- `defineBackground`'s `main` cannot be async; register listeners synchronously.
- Entrypoints are at most one level deep: `entrypoints/<name>/index.ts`, never
  `entrypoints/<group>/<name>/index.ts`. Use names like `youtube.content/`.
- Use `browser` (auto-imported, or `import { browser } from 'wxt/browser'`),
  not `chrome`. Guard optional APIs with feature detection (`browser.sidePanel?.…`).
- `runtime.onMessage` listeners answer with `sendResponse` + `return true`, not
  a returned promise; or use a messaging library (`@webext-core/messaging`).
- Content scripts: use `ctx` helpers (`ctx.addEventListener`, `ctx.setTimeout`,
  `ctx.isValid`) so code stops after the extension updates
  ("Extension context invalidated"). SPA sites: listen to `wxt:locationchange`.
- Styled UI on someone else's page → `createShadowRootUi` with
  `cssInjectionMode: 'ui'`; needs page JS access → `injectScript` of an
  unlisted script listed in `web_accessible_resources` (works on MV2 + MV3),
  not `world: 'MAIN'`.
- `storage` needs the `storage` permission and keys prefixed with
  `local:`/`session:`/`sync:`/`managed:`. Schema change → bump `version` and
  add a migration, never rename the key.
- Runtime env vars must start with `WXT_` or `VITE_` and are public in the
  bundle: no secrets. Built-ins: `import.meta.env.BROWSER`, `.MANIFEST_VERSION`,
  `.CHROME`, `.FIREFOX`, `.SAFARI`, `.EDGE`, `.OPERA`, `.COMMAND`, `.ENTRYPOINT`,
  `.MODE`, `.DEV`, `.PROD`.
- Routers in extension pages use hash mode (`createHashRouter`,
  `createWebHashHistory`, `createHashHistory`).
- Permissions are minimal and per browser; adding one on update can disable
  the extension for existing users until they accept (see `wxt:maintenance`).
