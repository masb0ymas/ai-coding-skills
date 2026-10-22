# vine layer patterns

Recipes for changes the generator does not cover. Snippets use vite syntax
where the framework matters; apply the vinext vs vite table in
`<plugin-root>/skills/scaffold/references/structure.md` for vinext
(`<plugin-root>` = `${CLAUDE_PLUGIN_ROOT}`). Every snippet below typechecks
against the vine reference apps.

## 1. Custom endpoint (non-CRUD action)

Add the call to the service next to the CRUD methods, type it in the
resources type, expose it through queries.

```ts
// lib/api/services/types/product.ts
import type { AxiosItemResponse, HTTP_METHOD, Resources } from '@/types/api'

export type ProductResources = Resources<ProductMethods, Models.Product> & {
  publish: (id: string) => Promise<AxiosItemResponse<Models.Product>>
}

// lib/api/services/product.ts
import type { Models } from '../models'
import { api } from '../client-fetch'

const resources = (): ProductResources => ({
  // Explicit generics: with an extra key, TS cannot infer the model from the return type.
  ...clientResource<string, ProductMethods, Models.Product>(path, methods),
  publish: (id: string) => api.post(`${path}/${id}/publish`),
})

// lib/api/queries/product.ts
const publish = () => {
  const qc = getQueryClient()
  return mutationOptions({
    mutationFn: async (id: string) => (await services.products.publish(id)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [PRODUCT_QUERY_KEY] }),
  })
}
export const productQueries = { list, get, create, update, delete: del, publish } as const
```

A resource with only custom calls (like `services/auth.ts`) skips
`clientResource` and declares its own `XResources` object type.

## 2. Fewer methods (read-only, PATCH instead of PUT)

Change the list in **both** `services/types/<x>.ts` (`XMethods`) and
`services/<x>.ts` (`methods`), then delete the query/UI pieces that called the
removed methods; `tsc` lists every one of them. `HTTP_METHOD.PATCH` → `edit()`,
`PUT` → `update()`.

## 3. Select fed by another resource (foreign key)

```tsx
// in form.tsx
const { data: categories, isLoading } = useQuery(queries.categories.list({ offset: 0, limit: 100 }))
const options = (categories?.data ?? []).map((c) => ({ label: c.name, value: c.id, original: c }))

<form.AppField
  name="category_id"
  children={(field) => (
    <field.SelectField asterisk label="Category" placeholder="Select a category" options={options} loading={isLoading} />
  )}
/>
```

`limit` is capped at 100 by the API; past that, add a search box or a
dedicated `/options` endpoint. Show the related name in the table from an
embedded relation (`?include=category`, `IncludeParam` in `dtos/paginate.ts`)
rather than one request per row.

## 4. Detail page

```tsx
// src/routes/(app)/master/product/$id.tsx  (vinext: app/(app)/master/product/[id]/page.tsx)
export const Route = createFileRoute('/(app)/master/product/$id')({
  // Prefetch so the page renders with data; the component reads the same cache.
  loader: ({ context, params }) => context.queryClient.ensureQueryData(queries.products.get(params.id)),
  component: () => <ProductDetail id={Route.useParams().id} />,
})
```

The detail block calls `useQuery(queries.products.get(id))`. In vinext the
page receives `params` as a promise (`{ params }: { params: Promise<{ id: string }> }`,
`const { id } = await params`) and passes `id` to a `'use client'` block; data is
fetched in the browser because the tokens live in browser cookies.

## 5. New form field component

1. `components/block/form/<name>-field.tsx`: `useFieldContext<T>()`,
   `Field` + `FieldLabel` + `FieldError`, same shape as `text-field.tsx`.
2. Register it in `hooks/form.tsx` `fieldComponents`; it is then
   `field.<Name>Field` in every `form.AppField`.

`NumberField` hands back strings; convert in the form
(`onValueChange={(v) => field.handleChange(v === '' ? undefined : Number(v))}`,
`value={field.state.value ?? ''}`) so the zod number schemas receive numbers.

## 6. Validation messages

Use the helpers in `lib/validation.ts` (`requiredString`, `optionalString`,
`requiredNonNegativeInteger`, `optionalNumber`, `requiredEnum`) so every
message reads "The <field> field is required." Add a new helper there when a
rule repeats in two schemas.

## 7. Environment variable

1. `config/env.ts`: add to `client` with a zod type; vinext also lists it in
   `runtimeEnv` as a literal `process.env.NEXT_PUBLIC_X` (only literal reads get inlined).
2. `.env.example` with a comment; Dockerfile `ARG` and the Cloudflare workflow
   `env` when it is needed at build time (`vine:deploy`).
3. Import `env` from `@/config/env`; the audit rejects direct reads elsewhere.

Prefix rules: `VITE_` / `NEXT_PUBLIC_` values ship to the browser and are
fixed at build time.

## 8. Menu and roles

`data/sidebar-menu.ts`: add the item to a `NAV_<GROUP>` constant, or create the
constant and add it to the role lists in `MENUS`. Hiding a menu item is not
access control: the API enforces permissions; route-level checks can read the
user's role from `queries.auth.profile()`.

## 9. Porting a feature between vinext and vite

Copy `lib/api/*` and `components/block/<group>/<resource>` unchanged, then
apply each row of the vinext vs vite table (directive, links, navigation,
page/route file, env). `audit_layers.py` flags any import left from the other framework.
