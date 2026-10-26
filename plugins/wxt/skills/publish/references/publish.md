# Publishing reference

## 1. Credentials (`.env.submit` locally, repository secrets in CI)

`wxt submit` reads flags, then environment variables named after them
(`--chrome-zip` → `CHROME_ZIP`), then `.env.submit`.

| Store | Variables | Where they come from |
|---|---|---|
| Chrome (API v2) | `CHROME_API_VERSION=v2`, `CHROME_EXTENSION_ID`, `CHROME_PUBLISHER_ID`, `CHROME_SERVICE_ACCOUNT_CLIENT_EMAIL`, `CHROME_SERVICE_ACCOUNT_PRIVATE_KEY` | extension ID and publisher ID from the CWS dashboard; a Google Cloud service account with the Chrome Web Store API enabled, its email added in the dashboard's account settings, and a JSON key |
| Firefox | `FIREFOX_EXTENSION_ID`, `FIREFOX_JWT_ISSUER`, `FIREFOX_JWT_SECRET` | `browser_specific_settings.gecko.id` (or the AMO UUID); API keys from addons.mozilla.org → Developer Hub → Manage API Keys |
| Edge | `EDGE_PRODUCT_ID`, `EDGE_CLIENT_ID`, `EDGE_API_KEY` | Partner Center → the extension's product ID; Publish API page for client ID and API key |
| Opera | `OPERA_PACKAGE_ID`, `OPERA_SESSION_ID` | addons.opera.com developer URL; session cookie |

Firefox ID: set it so updates and storage stay tied to the same add-on:

```ts
// wxt.config.ts
manifest: {
  browser_specific_settings: { gecko: { id: 'my-ext@example.com' } },
},
```

`wxt submit init` walks through all of this and writes `.env.submit`. Rotate
the service account key or AMO secret by re-running it.

## 2. Test the Firefox sources ZIP

```sh
rm -rf /tmp/src-check && mkdir /tmp/src-check
unzip -q .output/*-sources.zip -d /tmp/src-check
cd /tmp/src-check && pnpm i && pnpm zip:firefox
diff <(unzip -l .output/*-firefox.zip | awk '{print $4}' | sort) \
     <(unzip -l "$OLDPWD"/.output/*-firefox.zip | awk '{print $4}' | sort)
```

Same file list (and ideally identical hashes) → ready. Typical `zip` config:

```ts
zip: {
  includeSources: ['entrypoints', 'components', 'utils', 'assets', 'public',
                   'package.json', 'pnpm-lock.yaml', 'tsconfig.json', 'wxt.config.ts', 'README.md'],
  excludeSources: ['**/__tests__', '**/*.test.ts'],
  // dotSources: true,                       // only if a dotfile is needed to build
  // downloadPackages: ['@company/private'], // vendor private packages for reviewers (needs .npmrc)
},
```

Filename templates (0.21 defaults):
`artifactTemplate: '{{name}}-{{packageVersion}}-{{browser}}{{modeSuffix}}.zip'`,
`sourcesTemplate: '{{name}}-{{packageVersion}}-sources{{modeSuffix}}.zip'`.

## 3. Release checklist

- [ ] `version` bumped in `package.json`; changelog / store "What's new" text ready
- [ ] `pnpm compile`, entrypoint audit, `pnpm build`, `pnpm build:firefox` pass
- [ ] `.output/chrome-mv3/manifest.json` and `.output/firefox-mv2/manifest.json`
      read: permissions, host permissions, matches, version
- [ ] new permissions justified (CWS asks for a justification per permission;
      broad host permissions slow review)
- [ ] manual smoke test of the production build (Load unpacked / `about:debugging`)
- [ ] Firefox sources ZIP rebuilt per §2
- [ ] `wxt submit --dry-run` passes
- [ ] user confirmed the real submit

## 4. Self-hosting

- Firefox: `--firefox-channel unlisted` returns a signed XPI for your own
  update server (`browser_specific_settings.gecko.update_url`).
- Chromium outside the store only works through enterprise policy
  (`ExtensionInstallForcelist` + `update_url`); a plain `.crx` download is
  blocked for normal users.
