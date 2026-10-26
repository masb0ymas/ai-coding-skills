---
name: publish
description: Package and publish a WXT browser extension — `wxt zip` per browser, Firefox sources ZIP, `wxt submit init` / `wxt submit` to the Chrome Web Store (API v2 service account), Firefox Add-ons (AMO), and Edge Add-ons, dry runs, staged rollout, a GitHub Actions release workflow, Safari via Xcode, self-hosted/unlisted builds. Use for "publish", "release", "submit to the store", "zip the extension", "Chrome Web Store", "AMO", "CI release".
---

# wxt:publish — zip and submit

WXT zips builds and submits them through `publish-browser-extension`
(`wxt submit`). First listings are created by hand in each store dashboard;
WXT only ships updates.

| Store | ZIP | Submit flags |
|---|---|---|
| Chrome Web Store | `wxt zip` → `<name>-<version>-chrome.zip` | `--chrome-zip` |
| Firefox Add-ons | `wxt zip -b firefox` → `-firefox.zip` + `-sources.zip` | `--firefox-zip`, `--firefox-sources-zip` |
| Edge Add-ons | reuse the Chrome ZIP, or `wxt zip -b edge` | `--edge-zip` |
| Opera | Chrome ZIP | `--opera-zip` |
| Safari | `wxt build -b safari` then `xcrun safari-web-extension-packager .output/safari-mv2` | not automated |

## Workflow

1. **Pre-flight** (`wxt:maintenance` health check green), then:
   - bump `version` in `package.json` (stores reject a version they already
     have; `1.2.0-beta1` ships as `version 1.2.0` + `version_name`).
   - permission changes since the last release? They can disable the
     extension for existing users until accepted; call it out.
2. **Zip**:
   ```sh
   pnpm zip            # .output/<name>-<version>-chrome.zip
   pnpm zip:firefox    # .output/<name>-<version>-firefox.zip + -sources.zip (prints every file in it)
   ```
   Firefox reviewers rebuild from the sources ZIP: it must contain everything
   needed for `pnpm i && pnpm zip:firefox` to produce the same output, plus a
   `README.md` / `SOURCE_CODE_REVIEW.md` with those commands. Control it with
   `zip.includeSources` / `zip.excludeSources` / `zip.dotSources` in
   `wxt.config.ts` (an allowlist since 0.21); test it with
   `references/publish.md` §2. `.env` files change chunk hashes: delete them
   before zipping, or include a secret-free one via `zip.includeSources`.
3. **Secrets, once**: `pnpm wxt submit init` (interactive; the user runs it,
   e.g. `! pnpm wxt submit init`) writes `.env.submit`. Keep `.env.submit` in
   `.gitignore`. Chrome uses API **v2** with a service account; v1 refresh
   tokens stopped working on 2026-10-15. Credentials per store:
   `references/publish.md` §1.
4. **Dry run, then submit**:
   ```sh
   pnpm wxt submit --dry-run \
     --chrome-zip .output/*-chrome.zip \
     --firefox-zip .output/*-firefox.zip --firefox-sources-zip .output/*-sources.zip \
     --edge-zip .output/*-chrome.zip
   # same command without --dry-run once auth passes
   ```
   Submitting is outward-facing and not reversible: confirm with the user
   before dropping `--dry-run`. Useful flags: `--chrome-deploy-percentage 10`
   (staged rollout), `--chrome-publish-type STAGED_PUBLISH` (publish manually
   after approval), `--firefox-channel unlisted` (self-distributed, signed by AMO),
   `--*-skip-submit-review` (upload only).
5. **CI** (optional): copy `assets/release.yml` to
   `.github/workflows/release.yml`; add the secrets it lists in the repo
   settings. It runs on manual dispatch with a dry-run toggle. It needs
   `packageManager` in `package.json` (`wxt init` doesn't add it):
   `pnpm pkg set packageManager=pnpm@$(pnpm -v)`.
6. **Verify**: the dry run prints auth OK for every store; after the real
   submit, `pnpm wxt submit status` (or the dashboards) show the new version
   in review.

## Rules

- Never commit `.env.submit`, store keys, or a `.env` with secrets; never put
  them in the sources ZIP.
- One version per release across stores; build every ZIP from the same commit.
- MV2 Firefox and MV3 Chrome builds are both tested before submit
  (`pnpm build && pnpm build:firefox`), and the generated manifests read.
