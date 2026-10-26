---
name: migrate
description: Migrate an existing browser extension to WXT (wxt.dev) — from Plasmo, CRXJS, vite-plugin-web-extension, webpack/Parcel/Rollup setups, or a plain hand-written manifest.json — without changing the manifest users already accepted: entrypoints, manifest fields, assets, env vars, imports, storage and messaging libraries, and a before/after manifest comparison. Use for "migrate to WXT", "convert my Plasmo/CRXJS extension", "move this extension to WXT", "replace webpack in my extension".
---

# wxt:migrate — move an existing extension onto WXT

The migration is done when `wxt dev` runs, `wxt build` produces a working
extension, and the production manifest grants **exactly** the permissions and
host permissions the published version has. A new permission disables the
extension for existing users until they accept it.

For a new project use `wxt:scaffold`; for upgrading WXT itself use `wxt:maintenance`.

## Workflow

1. **Baseline.** On a clean branch, build the current extension for
   production and save its manifest(s) outside the build dir, e.g.
   `.migrate/old-chrome.json` (and `old-firefox.json` if Firefox ships). Note
   the store-relevant identity: `key`, `browser_specific_settings.gecko.id`,
   `update_url`. Also note how the old tool is run (scripts, env files, tags).
2. **Identify the source tool** and read its section in
   `references/sources.md`: Plasmo, CRXJS, vite-plugin-web-extension,
   webpack/other bundler, or plain files.
3. **Install WXT next to the old setup** (remove the old tool only after step 7):
   ```sh
   pnpm add -D wxt vite web-ext     # + @wxt-dev/module-react / -vue / -svelte / -solid
   pnpm dlx wxt@latest init .migrate/wxt-ref -t vanilla --pm pnpm < /dev/null   # reference files to copy from
   ```
   Copy in `wxt.config.ts`, `tsconfig.json` (`"extends": "./.wxt/tsconfig.json"`),
   and the scripts (`dev`, `build`, `zip`, `*:firefox`, `compile`,
   `"postinstall": "wxt prepare"`). If the project keeps sources in `src/`, set
   `srcDir: 'src'` instead of moving files.
4. **Move code, one entrypoint at a time** (mapping in `references/sources.md`):
   - manifest-listed pages/scripts → `entrypoints/<name>` per the
     `wxt:entrypoints` map; JS entrypoints get a default export
     (`defineBackground`, `defineContentScript`, `defineUnlistedScript`) with
     all runtime code inside `main()`.
   - per-entrypoint manifest fields (content script `matches`, `run_at`,
     `all_frames`, `world`; popup title/icon; options `open_in_tab`) → into
     the entrypoint file; everything else → `manifest` in `wxt.config.ts`.
   - files served as-is (icons, `_locales`, fonts, injected scripts) →
     `public/`; imported/bundled assets → `assets/`.
   - `chrome.*` → `browser.*` (same promise API on MV3); `process.env.X` →
     `import.meta.env.WXT_X` and rename the variables in `.env*`.
   - bundler-specific imports (`url:`, `data-base64:`, `?script`, webpack
     loaders, custom aliases) → Vite equivalents; aliases go in `alias` in
     `wxt.config.ts`.
   - Auto-imports may clash with existing names: set `imports: false` in
     `wxt.config.ts` during the migration and import from `#imports`.
5. **Keep the extension's identity**: same `name`, `version` (from
   `package.json`), `key` (if the old manifest had one), Firefox `gecko.id`,
   `default_locale`, and storage keys (WXT's `local:foo` reads the raw
   `chrome.storage.local` key `foo`, so existing data stays readable unless
   the old library encoded values differently — see Plasmo).
6. **Build and audit**:
   ```sh
   pnpm install && pnpm compile
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/entrypoints/scripts/audit_entrypoints.py --root .
   pnpm build && pnpm build:firefox
   ```
7. **Compare manifests** — the gate for finishing:
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/migrate/scripts/compare_manifests.py \
     .migrate/old-chrome.json .output/chrome-mv3/manifest.json
   ```
   Exit 1 means the new manifest requests more (permissions, host
   permissions, content script matches, manifest version change) — fix the
   config, don't accept it. Removed entries and changed fields are printed
   as warnings: each one must be explained (dropped feature) or fixed.
   Firefox: compare against `.output/firefox-mv2/manifest.json` (or
   `firefox-mv3` with `--mv3` if the old build was MV3; WXT defaults Firefox to MV2).
8. **Smoke test** the production build (load `.output/chrome-mv3` unpacked):
   every entrypoint opens/runs, settings saved by the old version are still
   there. Published on the Chrome Web Store → also run Google's
   extension-update-testing-tool to confirm no new permission prompt.
9. **Remove the old tool**: its dependencies, config files (`vite.config.ts`,
   `manifest.json`, `webpack.config.js`, `.plasmo/`, old build dirs), and
   `.migrate/` (keep the old manifests until release if useful). Update CI to
   the WXT scripts and `.output/` (see `wxt:publish`), `.gitignore`
   (`.output`, `.wxt`, `web-ext.config.ts`), and the README.
10. **Report**: what moved where, manifest comparison result, any warnings
    accepted and why, and follow-ups (re-enable auto-imports, adopt
    `storage.defineItem`, `wxt:publish` for the first WXT release).

## Rules

- Migrate in small commits (setup → each entrypoint → cleanup); the old build
  keeps working until the last step.
- Never widen permissions or `matches` to "make it work"; reproduce the old
  manifest first, refactor later.
- Don't rewrite working code during the migration (state libraries, storage
  wrappers, messaging): wrap or keep it, replace later.
- The first release after migration is a normal version bump; test the
  update path from the currently published version, not just a fresh install.
