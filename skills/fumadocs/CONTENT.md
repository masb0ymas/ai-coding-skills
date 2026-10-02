# Docs Content

For writing or editing pages under `apps/docs/content/docs/`. Wiring changes (collections, layout, loader) are out of scope → [APP.md](APP.md).

## File placement and slugs

Slugs derive from file path relative to `apps/docs/content/docs`:

| Path                    | Slugs            |
| ----------------------- | ---------------- |
| `./dir/page.mdx`        | `['dir','page']` |
| `./dir/index.mdx`       | `['dir']`        |
| `./(group)/page.mdx`    | `['page']`       |

Rules:

- One page per `.md`/`.mdx` file. `index.mdx` is the folder landing page.
- `(group)` folders organise without affecting slugs.
- The same URL MUST NOT appear twice in the page tree (Fumadocs locates the active item by pathname). No duplicated page entries across `meta.json` files.

## Frontmatter

```mdx
---
title: My Page
description: One-line summary shown under the title
icon: House
---
```

- `title` REQUIRED on every page. Body MUST NOT start with `# h1`; start at `##`.
- `description` RECOMMENDED; renders as `DocsDescription`.
- `icon` is a name resolved by the `loader()` icon handler, not a component import.

To add new frontmatter fields, change the collection schema first ([APP.md](APP.md)); content follows the schema, never the reverse. See [page conventions](https://www.fumadocs.dev/docs/page-conventions).

## Sidebar via meta.json

Each folder is ordered alphabetically unless its `meta.json` lists `pages`. When `pages` is present, unlisted items are excluded.

```json title="meta.json"
{
  "title": "Display Name",
  "pages": ["index", "getting-started", "---Section---", "...", "[Vercel](https://vercel.com)"]
}
```

Item syntax: `path` (page/folder), `---Label---` separator, `[Text](url)` link (`external:` prefix marks external), `...` rest (alphabetical), `z...a` reversed rest, `...folder` extract, `!item` exclude. Full reference: [page conventions](https://www.fumadocs.dev/docs/page-conventions).

Folder clicks land on the folder index (`index` file by default); override with `"pagesIndex": "overview"` (path or `[Text](url)` link).

For versioning or tabbed sections, mark the folder root in its `meta.json`:

```json
{ "title": "2.0.0", "root": "version" }
```

`root: true` renders as layout tabs; `root: "<type>"` groups interchangeable roots (e.g. versions) with a switcher dropdown. See [navigation](https://www.fumadocs.dev/docs/navigation).

## MDX authoring

GFM + JSX components. Internal links use framework `<Link/>` (prefetch, no hard reload); external links get `rel="noreferrer noopener" target="_blank"` automatically.

Available by default (no imports beyond shown):

- **Cards**: `<Cards><Card href title icon>…</Card></Cards>` for link grids; peers via `getPageTreePeers`.
- **Callouts**: `<Callout title type="info|warn|error|success|idea">…</Callout>`.
- **Code blocks**: fenced blocks with optional `title="…"`, `lineNumbers` (or `lineNumbers=4`), Shiki `// [!code highlight|++|--|focus]` and `// [!code word:…]` markers.
- **Headings**: anchors auto-generated (`Hello World` → `#hello-world`); `[!toc]` hides from TOC, `[toc]` TOC-only; `[#custom-id]` overrides anchor.
- **Tabs/Steps/Files/Accordion/TypeTable**: import from Fumadocs UI as needed; keep usage consistent with existing pages.

Full authoring reference: [markdown](https://www.fumadocs.dev/docs/markdown), [components](https://www.fumadocs.dev/docs/ui/components).

## Checklist

1. Frontmatter has `title`; body starts at `##`.
2. File placed so its derived slug is the intended URL; `(group)` used if the folder is organisational only.
3. Folder `meta.json` `pages` includes the new file (when `pages` is explicit); no URL duplicated anywhere in the tree.
4. `pnpm --filter @tera/docs dev`, open `http://localhost:3001/docs/<slug>`; sidebar order and TOC correct.
