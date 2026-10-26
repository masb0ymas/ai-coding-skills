# WXT maintenance runbook

## 1. Upgrading WXT

WXT is pre-1.0: every `0.X` bump is breaking, patch releases are not.

```sh
pnpm i -D wxt@latest --ignore-scripts   # skip postinstall: prepare fails until fixes are in
# apply the notes below for every version crossed
pnpm wxt prepare
bash health.sh .                        # then manual dev + production smoke test
```

Full notes: https://wxt.dev/guide/resources/upgrading.html. One `0.X` step per commit.

**0.20 → 0.21**
- Node ≥ 22, Vite ≥ 6.3.4, TypeScript ≥ 5.4. `vite` is a required peer
  (`pnpm add -D vite`); `web-ext` and `typescript` are optional peers. No
  `web-ext` installed → dev mode no longer opens the browser.
- `.wxt/tsconfig.json` is stricter (`verbatimModuleSyntax`,
  `noUncheckedIndexedAccess`, `module: Preserve`). Fix the type errors (use
  `import type` for types, handle `undefined` from index access); the
  `prepare:tsconfig` hook can revert temporarily.
- `url:` imports removed: install the npm package or vendor the file.
- ZIP names: default templates use `{{packageVersion}}` and `{{modeSuffix}}`;
  in custom templates `{{version}}` now means `manifest.version`, use
  `{{versionName}}` for the old value.
- `zip.includeSources` / `excludeSources` are a real allowlist now (+
  `zip.dotSources`); rebuild the lists and check the printed file list of
  `wxt zip -b firefox`.
- `createShadowRootUi` renders `<style>` + `<div>` instead of a full `<html>`:
  base styles need `:root, :host`. Pin `@webext-core/isolated-element@^1` to keep the old DOM.
- Content/unlisted scripts no longer expose a global: set `globalName: true`
  if `scripting.executeScript` reads the script's return value.
- `imports.eslintrc.enabled: true` now auto-detects the ESLint version.
- Removed: `runner` / `defineRunnerConfig` (→ `webExt` / `defineWebExtConfig`),
  `dev.server.hostname` (→ `host`), `wxt/testing` barrel (→
  `wxt/testing/fake-browser`, `wxt/testing/vitest-plugin`).
- `wxt submit` uses Chrome Web Store API v2 (service account); rerun
  `wxt submit init` (v1 stopped on 2026-10-15).
- fake-browser v2: mocked `runtime.onMessage` listeners must use `sendResponse` + `return true`.
- `useAppConfig` → `getAppConfig`.

**0.19 → 0.20**
- `browser` no longer uses `webextension-polyfill`: `runtime.onMessage`
  listeners can't answer by returning a promise (use `sendResponse` + `return true`),
  or keep the polyfill with `@wxt-dev/webextension-polyfill` in `modules`.
- `extensionApi` config removed. Types moved to the `Browser` namespace
  (`import { type Browser } from 'wxt/browser'`).
- Imports consolidated under `#imports` (`wxt/storage` → `wxt/utils/storage`, etc.);
  `.wxt/types/imports-module.d.ts` lists the real paths.

Other packages (`@wxt-dev/module-*`, `@wxt-dev/storage`, `@wxt-dev/i18n`,
`@wxt-dev/auto-icons`) upgrade with their own changelogs; one family per commit.

## 2. Dev mode

| Need | Fix |
|---|---|
| Browser doesn't open | install `web-ext` (`pnpm add -D web-ext`); check `disabled: true` in `webExt` / `web-ext.config.ts` |
| Don't open a browser | `web-ext.config.ts`: `defineWebExtConfig({ disabled: true })`, load `.output/chrome-mv3-dev` by hand |
| Stay logged in | `chromiumArgs: ['--user-data-dir=./.wxt/chrome-data']` (Windows: `chromiumProfile` absolute + `keepProfileChanges: true`) |
| Other browser binary | `binaries: { chrome: '/path/chrome-beta', firefox: 'firefoxdeveloperedition', edge: '/path/edge' }` |
| Start on a URL | `startUrls: ['https://example.com']` |
| Chrome AI / flags | `chromiumArgs: ['--disable-features=DisableLoadExtensionCommandLineSwitch']` or use your normal profile |
| Devcontainer / WSL | `wxt --host 0.0.0.0`, disable browser opening, `watchOptions: { usePolling: true, interval: 1000 }` |
| Only some entrypoints | `wxt -e popup -e background` |

`web-ext.config.ts` is per-developer (gitignored); shared defaults go in
`webExt` in `wxt.config.ts`; machine-wide defaults in `~/web-ext.config.ts`.

## 3. Debugging

| Symptom | Cause → fix |
|---|---|
| Build: `X is not implemented` / `document is not defined` | runtime code at module top level of an entrypoint → move into `main()`; `wxt prepare --debug` prints the pre-processed code |
| Build: `Default export not found` | helper file loose in `entrypoints/` → move to `utils/` or into an entrypoint folder |
| Build: `Multiple entrypoints with the same name` | `popup.html` + `popup.ts`, or `content.ts` + `content.css` → one folder with one `index.*`, import CSS from the script |
| Content script missing from `manifest.json` in MV3 dev | expected: registered at runtime for HMR. Check with `await chrome.scripting.getRegisteredContentScripts()` in the service worker console |
| Content script doesn't run | `matches` wrong (check the built manifest), page is an SPA (listen to `wxt:locationchange`), `include`/`exclude` drops it for this browser, or `registration: 'runtime'` |
| `Extension context invalidated` | old content script after reload/update → use `ctx.*` timers/listeners, check `ctx.isValid` |
| Page CSS breaks the injected UI | use `createShadowRootUi` + `cssInjectionMode: 'ui'` |
| UI size differs per site | `rem` relative to the host `<html>` → `postcss-rem-to-responsive-pixel` |
| Component library unstyled in shadow root | library injects `<style>` into `document.head` → point its container/style root at the shadow root |
| `storage` / API is `undefined` | permission missing in `manifest.permissions`, or API absent on this browser/MV → feature-detect |
| `onMessage` response is `undefined` | async listener returned a promise → `sendResponse` + `return true` |
| Env var `undefined` | not prefixed `WXT_`/`VITE_`, or read in `manifest` object form → function form |
| Router shows blank page | history mode → hash router |
| Background state lost | MV3 service worker was stopped → keep state in `storage` |
| Auto-import names unknown to TS/ESLint | run `wxt prepare`; ESLint: import `.wxt/eslint-auto-imports.mjs` |

## 4. Tests

Unit (Vitest):

```sh
pnpm add -D vitest
```

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import { WxtVitest } from 'wxt/testing/vitest-plugin';
export default defineConfig({ plugins: [WxtVitest()] });
```

```ts
// utils/__tests__/settings.test.ts
import { beforeEach, expect, it } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import { settings } from '../storage';

beforeEach(() => fakeBrowser.reset());
it('falls back to defaults', async () => {
  expect(await settings.getValue()).toEqual({ enabled: true, theme: 'light' });
});
```

The plugin provides the in-memory `browser` (storage works without mocks),
auto-imports, aliases, and `import.meta.env.BROWSER`/`MANIFEST_VERSION`. To
mock a WXT helper, mock its real path (`vi.mock('wxt/utils/inject-script')`),
not `#imports`. Add `"test": "vitest run"` to `package.json`.

E2E: Playwright with a persistent Chromium context and
`--load-extension=<root>/.output/chrome-mv3` (`pnpm build` first). Example:
https://github.com/wxt-dev/examples/tree/main/examples/playwright-e2e-testing.

## 5. Updates and permissions

- Logic on update: `browser.runtime.onInstalled.addListener(({ reason, previousVersion }) => { if (reason === 'update') ... })`
  in the background `main()`; unit-test it with `fakeBrowser.runtime.onInstalled.trigger(...)`.
- New permissions or host permissions can disable the extension until users
  accept. Prefer `optional_permissions` + `browser.permissions.request()`.
  Test with https://github.com/GoogleChromeLabs/extension-update-testing-tool
  (Chromium) or Firefox's "Test Permission Requests" guide.
- Stored data shape changes → versioned `storage.defineItem` with migrations.
