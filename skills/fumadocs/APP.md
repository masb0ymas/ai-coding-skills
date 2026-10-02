# Docs App Wiring

For collections, loader, layouts, and MDX setup in `apps/docs`. Content edits (pages, `meta.json`) are out of scope → [CONTENT.md](CONTENT.md).

## Map

| File                                            | Role                                                              |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| `source.config.ts`                              | Collection definitions (`defineDocs`, `dir: 'content/docs'`)      |
| `lib/source.ts`                                 | `loader({ baseUrl: '/docs', source: docs.toFumadocsSource() })`   |
| `app/docs/layout.tsx`                           | `DocsLayout tree={source.pageTree}` + `nav`, `githubUrl`          |
| `app/docs/[[...slug]]/page.tsx`                 | `source.getPage(slug)` → `DocsPage` + `MDXContent`                |
| `components/mdx-components.tsx`                 | `getMDXComponents()` (currently bare `defaultMdxComponents`)      |
| `app/layout.tsx` + `app/global.css`             | `RootProvider` shell; Fumadocs UI CSS (`glass`, `neutral`, `preset`) |
| `next.config.mjs`                               | `createMDX()` from `fumadocs-mdx/next` wraps Next config (ESM-only) |

`source.config.ts` uses the Config API (entry files generated under `.source/`). Do NOT mix in the macro API (`fumadocs-mdx/macro`) or hand-edit `.source/`. See [MDX](https://www.fumadocs.dev/docs/mdx), [Next.js setup](https://www.fumadocs.dev/docs/mdx/next).

## Operations

**Extend frontmatter / folder fields.** Edit `source.config.ts` schema:

```ts
import { pageSchema, metaSchema } from 'fumadocs-core/source/schema'

export const docs = defineDocs({
  docs: { schema: pageSchema.extend({ index: z.boolean().default(false) }) },
  meta: { schema: metaSchema.extend({ /* extra props */ }) },
})
```

Validation runs at build time; output MUST be serializable. See [collections](https://www.fumadocs.dev/docs/mdx/collections).

**Change loader behaviour.** Edit `lib/source.ts` only: `baseUrl`/`url()`, custom `slugs()`, `icon()` handler (map name → JSX, e.g. via `lucide-react`), `i18n` config. API: [loader](https://www.fumadocs.dev/docs/headless/source-api).

**Change docs chrome.** Edit `app/docs/layout.tsx` (`DocsLayout` props: `tree`, `nav`, `links`, `sidebar`, `tabs`). Sidebar items render from the page tree; tabs come from root folders or explicit `tabs` prop. See [docs layout](https://www.fumadocs.dev/docs/ui/layouts/docs), [overview](https://www.fumadocs.dev/docs/ui).

**Change page rendering.** Edit `app/docs/[[...slug]]/page.tsx` (`DocsPage`/`DocsTitle`/`DocsDescription`/`DocsBody`), `components/mdx-components.tsx` (extend `defaultMdxComponents`; relative links via `createRelativeLink(source, page)`), `app/layout.tsx` (`RootProvider` required for search/theme). See [components](https://www.fumadocs.dev/docs/ui/components).

**Static export / i18n / search.** Follow [deploying](https://www.fumadocs.dev/docs/deploying/static), [i18n](https://www.fumadocs.dev/docs/internationalization), [search](https://www.fumadocs.dev/docs/search) against this repo's wiring; don't copy standalone-starter snippets verbatim (paths/loader here already exist).

## Guardrails

- Node.js ≥ 22. `postinstall` runs `fumadocs-mdx` (typegen); `typecheck` is `next typegen && tsc --noEmit`.
- Next.js breaking changes vs training data: read `node_modules/next/dist/docs/` (from `apps/docs/`) before touching `app/` or `next.config`.
- Dynamic route `[[...slug]]`: keep `generateStaticParams` from `source.generateParams()` when adding it; static export stays fast.

## Checklist

1. Change confined to the owning file in the map above; no parallel convention introduced.
2. `pnpm --filter @tera/docs typecheck` passes.
3. `pnpm --filter @tera/docs dev`, open `http://localhost:3001/docs`; layout, page, and sidebar render.
