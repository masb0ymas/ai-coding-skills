---
name: fumadocs
description: Work on the Fumadocs docs site in apps/docs (Next.js + Fumadocs MDX). Use when writing or editing docs content under content/docs, changing sidebar/navigation via meta.json, or touching docs wiring (source.config.ts, lib/source.ts, docs layout, slug page, MDX components).
---

# Fumadocs

Docs site lives in `apps/docs`. Content source is Fumadocs MDX (Config API); routing by Next.js App Router.

## Pick a branch

- **Writing or editing docs content** (new page, frontmatter, sidebar order, MDX components) → read [CONTENT.md](CONTENT.md) and follow it.
- **Changing docs wiring** (collections/schema, loader, layout, slug page, MDX setup, theming) → read [APP.md](APP.md) and follow it.

Wrong branch wastes the whole change: content edits never touch `lib/` or `app/` wiring; wiring changes never hand-write slugs or sidebar trees.

## Rules for both

1. **Follow the existing wiring, don't re-derive it.** `apps/docs/lib/source.ts`, `apps/docs/source.config.ts`, `apps/docs/app/docs/layout.tsx`, `apps/docs/app/docs/[[...slug]]/page.tsx` are the source of truth. Match their patterns; don't introduce a second convention (e.g. macro API alongside the Config API).
2. **Slugs and sidebar are generated, never hardcoded.** File paths under `apps/docs/content/docs` plus `meta.json` produce slugs and the page tree via `loader()`. No manual route lists.
3. **Title comes from frontmatter, not `# h1`.** Every doc file needs `title` in frontmatter; body starts at `##`.
4. **Next.js here is not training-data Next.js.** Before writing any `app/` or `next.config` code, read the versioned guide in `node_modules/next/dist/docs/` (resolved from `apps/docs/`). Heed deprecations.
5. **Verify by running.** Content: `pnpm --filter @tera/docs dev` (port 3001) and open the page. Wiring: also run `typecheck` in `apps/docs` (`next typegen && tsc --noEmit`). Generated `.source/` output is build artifact, never edited by hand.
