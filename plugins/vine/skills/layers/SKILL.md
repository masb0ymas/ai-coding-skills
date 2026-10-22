---
name: layers
description: Keep a vine-style React frontend (vinext or Vite + TanStack Router) inside its layers — lib/api models, dtos, services, queries, components/block and components/ui, pages/routes, sidebar menu — when adding or changing features. Use to add a resource/CRUD page, API endpoint call, form, table, component, route or menu entry, to port code between vinext and vite, or to audit layer violations.
---

# vine:layers — API and component layers

Every change lands in one layer with one job. This skill has the layer
contracts, a CRUD generator, and an automated audit. No vine app yet → `vine:scaffold`.

## Layer contracts

| Layer | Job | Imports allowed |
|---|---|---|
| `lib/api/models` | response shapes (`Models.X` namespace) | `import type` only |
| `lib/api/dtos` | zod request schemas via `lib/validation` helpers; `XFormDto` | zod, `lib/validation` |
| `lib/api/services` | HTTP: `clientResource(path, methods)` or explicit `api.get/post`; registered in `services/index.ts` | `client-fetch`, `resource`, `types/api`, dto/model types |
| `lib/api/queries` | `queryOptions` / `mutationOptions`, query keys, invalidation; registered in `queries/index.ts` | `services`, `getQueryClient`, dto types |
| `components/ui` | shadcn primitives, no app knowledge | ui libs, `lib/utils` |
| `components/block/common`, `block/form` | reusable composites and form fields | `ui` |
| `components/block/<group>/<resource>` | feature UI: `table.tsx`, `column.tsx`, `form.tsx` | `queries`, dtos, `parseDto`, `axios-error`, `ui`, `block/*` |
| pages (`app/`) / routes (`src/routes/`) | guard + render one block component | `block`, `lib/auth/handler` |
| `config/env.ts` | the only env reader | — |
| `data/sidebar-menu.ts` | menus per role, only existing routes | — |

UI reaches the API only through `queries`. Code and recipes:
`references/patterns.md`. Framework-specific rows (page files, `'use client'`,
links, env prefix): the vinext vs vite table in
`${CLAUDE_PLUGIN_ROOT}/skills/scaffold/references/structure.md`.

## Workflow

1. **Read the reference module first**: `components/block/master/organization/*`
   and `lib/api/*/organization.ts` show every convention the new code copies.
2. **New CRUD resource → the generator** (Python stdlib; detects vinext/vite):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/layers/scripts/new_resource.py --root . --name product \
     --fields "name:string:required,price:int:required,description:text,active:bool,released_at:date"
   ```
   - types `string text uuid date int float bool`, flag `required`.
   - `--group master` (default; folder, URL segment, and `NAV_<GROUP>` menu),
     `--plural`, `--api-path` (default `/api/v1/<plural>`), `--no-route`,
     `--no-menu`, `--force`, `--dry-run`.
   - Writes model, dto schema, service + method types, queries, column/form/table,
     the page (vinext) or route (vite, then regenerates `routeTree.gen.ts`), and
     registers models/services/queries/menu.
   - Afterwards adjust what it cannot guess: foreign keys as selects
     (patterns §3), read-only resources (trim methods, patterns §2), menu roles in
     `MENUS`, table description, columns to hide.
3. **Everything else by hand** with the recipes in `references/patterns.md`:
   custom endpoints, selects fed by another resource, detail pages, route
   loaders, new form fields, env vars, porting between vinext and vite.
4. **Verify** — done when all three pass:
   ```sh
   pnpm exec tsc --noEmit
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/layers/scripts/audit_layers.py --root .
   pnpm build
   ```
   The audit fails on UI calling services/axios directly, services importing
   React Query or UI, runtime imports in models, env read outside
   `config/env.ts`, next/* in a vite app (or TanStack Router in vinext), and
   vinext pages using hooks without `'use client'`; it warns on unregistered
   services/queries/models.

## Hard rules

- Request bodies go through `parseDto(schema, value)` before the mutation; the
  schema is the one in `lib/api/dtos`, shared by the form validators.
- Errors surface with `toastAxiosError(error)`; it already reads the API's
  `errors[]` list.
- Query keys start with the resource constant (`X_QUERY_KEY`) so one
  `invalidateQueries({ queryKey: [X_QUERY_KEY] })` refreshes lists and details.
- Service method lists are typed by `XMethods`: `resource()` builds only the
  methods it is given, so the declared type and the runtime list stay identical.
- List state (page, pageSize, search) lives in the URL via nuqs
  (`usePaginationQuery`, `useQueryState`).
- New UI primitives come from shadcn (`pnpm dlx shadcn@latest add <name>`) into
  `components/ui`; reuse `block/common` before writing a new composite.
