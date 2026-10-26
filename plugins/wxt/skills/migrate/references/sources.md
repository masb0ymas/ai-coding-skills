# Migration maps per source tool

Read the source project's files before applying a row: these are the common
shapes, and projects drift from them. WXT targets below follow `wxt:entrypoints`.

## 1. Plasmo

| Plasmo | WXT |
|---|---|
| `popup.tsx`, `options.tsx`, `sidepanel.tsx`, `newtab.tsx` (component default export) | `entrypoints/<name>/index.html` + `main.tsx` that mounts the component + the component file (copy the shape of the React template popup) |
| `tabs/<page>.tsx` (served at `tabs/<page>.html`) | unlisted page `entrypoints/<page>/index.html` + `main.tsx`; URL becomes `/<page>.html`, update every `chrome.runtime.getURL("tabs/...")` |
| `background.ts` / `background/index.ts` | `entrypoints/background.ts` with `defineBackground(() => { ... })` |
| `contents/<name>.ts` + `export const config: PlasmoCSConfig = { matches, run_at, all_frames, world }` | `entrypoints/<name>.content.ts`, options moved into `defineContentScript({ matches, runAt, allFrames, world, main(ctx) { ... } })` |
| CSUI `contents/<name>.tsx` (component default export, `getStyle`, `getInlineAnchor`/`getOverlayAnchor`, `getShadowHostId`) | `entrypoints/<name>.content/index.tsx` with `createShadowRootUi` (`cssInjectionMode: 'ui'`, `import './style.css'`, `anchor`, `position: 'inline' \| 'overlay'`); `getStyle` CSS → imported stylesheet |
| `assets/` (icon source, files referenced at runtime) | `public/`; icon generation from `assets/icon.png` → `@wxt-dev/auto-icons` module or pre-sized `public/icon/<size>.png` |
| `"manifest"` overrides in `package.json` (`permissions`, `host_permissions`, `web_accessible_resources`, ...) | `manifest` in `wxt.config.ts` |
| `~` / `~/*` alias (project root or `src`) | WXT `~`/`@` = srcDir, `~~`/`@@` = root: set `srcDir` so existing `~` imports still resolve, or add `alias` |
| `url:`, `data-base64:`, `data-text:` imports | `url:` (remote code) is not supported: npm package or vendored file. `data-text:` → `?raw`, `data-base64:` → `?inline` (Vite) or a `public/` file |
| `process.env.PLASMO_PUBLIC_X` | `import.meta.env.WXT_X`; rename in `.env*` |
| `plasmo build --tag=<tag>` / `.env.<tag>` | `wxt build --mode <mode>` / `.env.<mode>` |
| `plasmo build --target=firefox-mv2` | `wxt build -b firefox` (MV2 default) / `--mv3` |
| `@plasmohq/storage` (`new Storage()`, `useStorage`) | keep it during the migration; later `storage.defineItem`. Plasmo's `Storage` stores values JSON-serialised (strings), WXT stores raw values: reading old keys with WXT needs a parse step or a versioned migration. Confirm by inspecting `chrome.storage.local.get()` in the old build |
| `@plasmohq/messaging` (`background/messages/*.ts`, `sendToBackground`) | keep, or move to `@webext-core/messaging` handlers registered in `defineBackground`'s `main` |
| `build/chrome-mv3-prod/manifest.json` | baseline manifest for `compare_manifests.py` |

Remove afterwards: `plasmo`, `@plasmohq/*` you replaced, `.plasmo/`, `build/`.

## 2. CRXJS (`@crxjs/vite-plugin`)

CRXJS discovers entrypoints from the manifest; WXT discovers them from files.

| CRXJS | WXT |
|---|---|
| `manifest.json` or `manifest.config.ts` (`defineManifest`) | entrypoint options into the entrypoint files; the rest into `manifest` in `wxt.config.ts` (function form if it used env/mode) |
| `background.service_worker: 'src/background.ts'` (+ `type: 'module'`) | `entrypoints/background.ts`, `defineBackground({ type: 'module', main() {} })` if ESM was required |
| `content_scripts[].js: ['src/content.ts']` + `matches` | `entrypoints/<name>.content.ts` with `matches` etc. in `defineContentScript` |
| `action.default_popup: 'src/popup/index.html'` | `entrypoints/popup/index.html` (title and icon as `<title>` / `<meta name="manifest.*">`) |
| `options_page` / `options_ui` / `side_panel.default_path` / `chrome_url_overrides` / `devtools_page` | `options/`, `sidepanel/`, `newtab/`, `history/`, `bookmarks/`, `devtools/` entrypoints |
| extra pages in `build.rollupOptions.input` | unlisted pages `entrypoints/<name>.html` |
| `import scriptPath from './inject?script'` (dynamic injection) | content script with `registration: 'runtime'` + `browser.scripting.executeScript({ files: ['content-scripts/<name>.js'] })`, or an unlisted script + `injectScript('/<name>.js')` |
| `vite.config.ts` plugins / `resolve.alias` / `define` | `vite: () => ({ plugins: [...], define: {...} })` and `alias` in `wxt.config.ts`; framework plugin → `@wxt-dev/module-*`. Delete `vite.config.ts` |
| `tsconfig.json` paths | `extends: "./.wxt/tsconfig.json"`, aliases moved to `wxt.config.ts` |
| `dist/manifest.json` | baseline manifest |

Start with `imports: false` unless the project already used `unplugin-auto-import`.
Example migration: https://github.com/aklinker1/github-better-line-counts/commit/39d766d2ba86866efefc2e9004af554ee434e2a8

## 3. vite-plugin-web-extension

Same as CRXJS: entrypoints listed in `manifest.json` (and `additionalInputs`)
become files in `entrypoints/`; `browser` templating in the manifest
(`{{chrome}}.permissions`, `{{firefox}}.…`) becomes the function form
`manifest: ({ browser }) => ({ ... })`; `vite.config.ts` settings move to
`vite: () => ({ ... })`. Baseline: `dist/manifest.json`.

## 4. webpack / Parcel / Rollup / esbuild setups

- Entries in the bundler config (`entry: { background, content, popup }`) →
  one WXT entrypoint each; HTML from `html-webpack-plugin` → the entrypoint's
  `index.html` with `<script type="module" src="./main.ts">`.
- `copy-webpack-plugin` patterns → `public/`.
- `DefinePlugin` / `process.env.*` → `import.meta.env.WXT_*` (or `vite.define`).
- Loaders: CSS/SCSS/PostCSS work in Vite by installing the preprocessor;
  `svgr` → `vite-plugin-svgr`; `raw-loader` → `?raw`; `url-loader`/`file-loader` → plain imports.
- `webextension-polyfill` imports: drop them (WXT's `browser` is native) or
  keep via the `@wxt-dev/webextension-polyfill` module; listeners that return
  promises need it.
- Baseline: the manifest in the old output dir.

## 5. Plain files (no bundler, `manifest.json` at the root)

- Each script listed in the manifest → an entrypoint; wrap the file body in
  `main()` (`defineBackground(() => { ...old body... })`). Scripts loaded via
  `<script src>` in HTML pages stay plain modules imported by the page's `main.ts`.
- MV2 `background.scripts: [a.js, b.js]` sharing globals → one
  `background/index.ts` importing `./a` and `./b` as modules; replace implicit
  globals with exports.
- Files injected with `chrome.scripting.executeScript({ files })` → content
  script with `registration: 'runtime'` or an unlisted script; update the paths
  to the WXT output names (`content-scripts/<name>.js`, `<name>.js`).
- Everything else (icons, `_locales`, images) → `public/` keeping relative
  paths, so `getURL` calls and `__MSG_*__` keep working.

## 6. Manifest fields that move to entrypoints

| manifest.json | WXT |
|---|---|
| `content_scripts[i].matches / exclude_matches / include_globs / exclude_globs` | `matches`, `excludeMatches`, `includeGlobs`, `excludeGlobs` |
| `content_scripts[i].run_at / all_frames / match_about_blank / match_origin_as_fallback / world` | `runAt`, `allFrames`, `matchAboutBlank`, `matchOriginAsFallback`, `world` |
| `content_scripts[i].css` | `import './style.css'` in the script |
| `background.persistent` (MV2) / `background.type` | `defineBackground({ persistent, type })` |
| `action.default_title` / `default_icon` | popup `<title>` / `<meta name="manifest.default_icon">` |
| `options_ui.open_in_tab` | `<meta name="manifest.open_in_tab" content="true">` |
| `side_panel` / `sidebar_action` | `sidepanel` entrypoint (WXT writes both per browser) |
| `version` / `version_name` | `package.json` `version` |
| `name`, `description` | `package.json` or `manifest` (keep `__MSG_*__` values) |

Everything else (`permissions`, `optional_permissions`, `host_permissions`,
`web_accessible_resources`, `commands`, `content_security_policy`, `key`,
`browser_specific_settings`, `externally_connectable`, `declarative_net_request`,
`oauth2`, `minimum_chrome_version`, `default_locale`) → `manifest` in
`wxt.config.ts`, MV3 shape preferred.
