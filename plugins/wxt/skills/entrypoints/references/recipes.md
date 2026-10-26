# WXT recipes

Code that follows WXT 0.21 (wxt.dev). Auto-imports cover `defineBackground`,
`defineContentScript`, `defineUnlistedScript`, `browser`, `storage`,
`createShadowRootUi`, `createIntegratedUi`, `createIframeUi`, `injectScript`,
`MatchPattern`, `getAppConfig`; without auto-imports import them from `#imports`.
Paths below are relative to `srcDir` (default: project root).

## 1. Background

```ts
// entrypoints/background.ts
export default defineBackground({
  type: 'module',                 // optional, MV3 ESM service worker
  main() {                        // not async: listeners must register synchronously
    browser.runtime.onInstalled.addListener(({ reason }) => {
      if (reason === 'install') browser.tabs.create({ url: browser.runtime.getURL('/welcome.html') });
    });
    browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === 'get-tab-title') {
        browser.tabs.get(sender.tab!.id!).then((tab) => sendResponse(tab.title));
        return true;              // keep the channel open for the async answer
      }
    });
  },
});
```

MV3 service workers stop when idle: keep state in `storage`, not in variables.
Toolbar click without a popup: delete the popup entrypoint, add `action: {}` to
`manifest`, then `(browser.action ?? browser.browser_action).onClicked.addListener(...)`.

## 2. Content script

```ts
// entrypoints/github.content.ts
export default defineContentScript({
  matches: ['*://github.com/*'],
  runAt: 'document_idle',         // document_start | document_end | document_idle
  // allFrames, excludeMatches, includeGlobs, excludeGlobs, matchAboutBlank
  // include: ['chrome'] / exclude: ['firefox'] to drop it from some builds
  // per-browser values: matches: { chrome: [...], firefox: [...] }
  main(ctx) {
    const onKey = (e: KeyboardEvent) => { /* ... */ };
    ctx.addEventListener(window, 'keydown', onKey);   // removed when ctx is invalidated
    ctx.setInterval(() => { /* ... */ }, 1000);
  },
});
```

CSS for the script: `import './style.css'` inside `github.content/index.ts`
(added to the manifest `css` array), unless the UI uses `cssInjectionMode: 'ui'`.

SPA sites (no full reload on navigation):

```ts
const watch = new MatchPattern('*://*.youtube.com/watch*');
export default defineContentScript({
  matches: ['*://*.youtube.com/*'],
  main(ctx) {
    ctx.addEventListener(window, 'wxt:locationchange', ({ newUrl }) => {
      if (watch.includes(newUrl)) mount(ctx);
    });
  },
});
```

Inject on demand instead of on every page: `registration: 'runtime'` in the
content script, `scripting` permission, then from the background
`browser.scripting.executeScript({ target: { tabId }, files: ['content-scripts/<name>.js'] })`.
To read the value returned from `main` in `result[0].result`, also set
`globalName: true` on the content script (default `false` since 0.21).

## 3. Content script UI

| Helper | Page CSS leaks in | Isolated events | HMR | Page DOM access |
|---|---|---|---|---|
| `createIntegratedUi` | yes | no | no | yes |
| `createShadowRootUi` | no | opt-in (`isolateEvents`) | no | yes |
| `createIframeUi` | no | yes | yes | no |

Shadow root with React:

```tsx
// entrypoints/overlay.content/index.tsx
import './style.css';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

export default defineContentScript({
  matches: ['<all_urls>'],
  cssInjectionMode: 'ui',
  async main(ctx) {
    const ui = await createShadowRootUi(ctx, {
      name: 'my-overlay',               // custom element name, must contain a dash
      position: 'inline',               // inline | overlay | modal
      anchor: 'body',                   // selector, element, or () => element
      onMount(container) {
        const el = document.createElement('div');
        container.append(el);           // React warns on rendering into body
        const root = ReactDOM.createRoot(el);
        root.render(<App />);
        return root;
      },
      onRemove: (root) => root?.unmount(),
    });
    ui.mount();                         // or ui.autoMount() to follow a dynamic anchor
  },
});
```

Vue: `createApp(App).mount(container)` / `app.unmount()`. Svelte:
`mount(App, { target: container })` / `unmount(app)`. Solid:
`render(() => <App />, container)` returns the unmount function.

Tailwind or `rem`-based CSS inside a shadow root scales with the host page's
`<html>` font size: convert `rem` → `px` with `postcss-rem-to-responsive-pixel`.
Component libraries that inject `<style>` into `document.head` (Ant Design,
Mantine, MUI/emotion) need their container/root option pointed at the shadow root.

IFrame UI: an unlisted page `entrypoints/panel.html`, listed in
`web_accessible_resources`, then
`createIframeUi(ctx, { page: '/panel.html', position: 'inline', anchor: 'body' })`.

## 4. Main world (page JS access)

```ts
// entrypoints/page-bridge.ts  (unlisted script)
export default defineUnlistedScript(() => {
  const script = document.currentScript;
  script?.addEventListener('from-content', (e) => { /* (e as CustomEvent).detail */ });
  script?.dispatchEvent(new CustomEvent('from-page', { detail: (window as any).somePageGlobal }));
});
```

```ts
// entrypoints/bridge.content.ts
export default defineContentScript({
  matches: ['*://example.com/*'],
  async main() {
    const { script } = await injectScript('/page-bridge.js', {
      keepInDom: true,
      modifyScript(s) { s.addEventListener('from-page', (e) => { /* ... */ }); },
    });
    script.dispatchEvent(new CustomEvent('from-content', { detail: 'hi' }));
  },
});
```

```ts
// wxt.config.ts
manifest: {
  web_accessible_resources: [{ resources: ['page-bridge.js'], matches: ['*://example.com/*'] }],
},
```

## 5. Popup / options / side panel with a framework

```text
entrypoints/popup/
  index.html   <title> = action.default_title; <meta name="manifest.default_icon" ...>
  main.tsx     createRoot(document.getElementById('root')!).render(<App />)
  App.tsx
  style.css
```

```html
<!-- entrypoints/options/index.html -->
<head>
  <title>Settings</title>
  <meta name="manifest.open_in_tab" content="true" />
</head>
<body><div id="root"></div><script type="module" src="./main.tsx"></script></body>
```

Side panel: `entrypoints/sidepanel/index.html`; WXT adds the `sidePanel`
permission on Chrome and maps to `sidebar_action` on Firefox. Open it from the
action click (Chrome):
`browser.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })` in the background.

Routing: hash mode only (`createHashRouter`, `createWebHashHistory`,
TanStack `createHashHistory()`), the page path is fixed at `/popup.html`.

## 6. Storage

```ts
// utils/storage.ts  (auto-imported everywhere)
export const settings = storage.defineItem<{ enabled: boolean; theme: 'light' | 'dark' }>(
  'sync:settings',
  { fallback: { enabled: true, theme: 'light' } },
);
export const installId = storage.defineItem('local:installId', {
  init: () => crypto.randomUUID(),
});
```

```ts
await settings.getValue();
await settings.setValue({ ...(await settings.getValue()), enabled: false });
const unwatch = settings.watch((next, prev) => { /* sync UI */ });
```

- Areas: `local` (default choice), `sync` (small, synced; ~100 KB total, 8 KB
  per item), `session` (memory, cleared on browser restart), `managed` (policy, read-only).
- Changing the shape: add `version: 2` and `migrations: { 2: (old) => next }`.
  Unversioned items count as version 1.
- Many values at once: `storage.getItems` / `setItems`.
- Requires `permissions: ['storage']`.

## 7. Messaging

Vanilla: `browser.runtime.sendMessage(msg)` (to background),
`browser.tabs.sendMessage(tabId, msg)` (to a content script); listeners per §1.
Typed alternative:

```ts
// utils/messaging.ts
import { defineExtensionMessaging } from '@webext-core/messaging';
interface Protocol {
  getTabTitle(): string;
  setBadge(text: string): void;
}
export const { sendMessage, onMessage } = defineExtensionMessaging<Protocol>();
```

```ts
onMessage('getTabTitle', ({ sender }) => sender.tab?.title ?? '');   // background main()
const title = await sendMessage('getTabTitle');                       // content script
```

## 8. Manifest, env, runtime config

```ts
// wxt.config.ts
export default defineConfig({
  manifest: ({ browser, manifestVersion, mode }) => ({
    permissions: browser === 'firefox' ? ['storage', 'webRequest'] : ['storage', 'declarativeNetRequest'],
    host_permissions: ['https://api.example.com/*'],
    commands: { 'toggle': { suggested_key: { default: 'Alt+Shift+T' }, description: 'Toggle' } },
    oauth2: { client_id: import.meta.env.WXT_GOOGLE_CLIENT_ID, scopes: ['openid'] },
  }),
});
```

- Write MV3 shapes (`action`, `web_accessible_resources` objects,
  `host_permissions`); WXT converts them for MV2 builds.
- Env files: `.env`, `.env.[mode]`, `.env.[browser]`, `.env.[mode].[browser]`
  (+ `.local`). Reading env in `manifest` needs the function form.
- `app.config.ts` + `getAppConfig()` collects typed runtime config in one place:

```ts
// app.config.ts
declare module 'wxt/utils/define-app-config' {
  export interface WxtAppConfig { apiUrl: string }
}
export default defineAppConfig({ apiUrl: import.meta.env.WXT_API_URL ?? 'https://api.example.com' });
```

- Per-browser code: `if (import.meta.env.FIREFOX) { ... }`. Default targets:
  MV3 for Chromium, MV2 for Firefox and Safari; force with `--mv3` / `--mv2`.

## 9. i18n

`manifest: { default_locale: 'en', name: '__MSG_extName__', description: '__MSG_extDescription__' }`,
`public/_locales/<lang>/messages.json`, `browser.i18n.getMessage('key')`.
Typed keys and YAML sources: `@wxt-dev/i18n` (module `@wxt-dev/i18n/module`,
messages in `locales/<lang>.yml`, `i18n.t('key')`).

## 10. Icons, assets, modules

- `public/` is copied as-is (`browser.runtime.getURL('/file.png')`); `assets/`
  is bundled (`import logo from '@/assets/logo.svg'`). In content scripts, URLs
  of public files need `web_accessible_resources`.
- One source icon → all sizes: `@wxt-dev/auto-icons` in `modules`.
- Local build logic: `modules/<name>.ts` with `defineWxtModule({ setup(wxt) { wxt.hook('build:manifestGenerated', (_, manifest) => { ... }) } })`.
- Aliases: `@`/`~` = srcDir, `@@`/`~~` = root. New aliases go in `alias` in
  `wxt.config.ts`, never in `tsconfig.json`.
