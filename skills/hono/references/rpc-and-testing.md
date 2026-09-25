# Hono RPC & Testing

Source: https://hono.dev/docs/guides/rpc, https://hono.dev/docs/guides/testing, https://hono.dev/docs/helpers/testing

## RPC: share the API spec server → client via types

### Server

Chain routes (or assign the final call to a variable), export the type:

```ts
const route = app.post(
  '/posts',
  zValidator('form', z.object({ title: z.string(), body: z.string() })),
  (c) => c.json({ ok: true, message: 'Created!' }, 201)
)
export type AppType = typeof route
```

Status codes passed explicitly to `c.json(payload, status)` become discriminated union members on the client.

### Client

```ts
import { hc } from 'hono/client'
import type { AppType } from './server'

const client = hc<AppType>('http://localhost:8787/')

// path segments become client objects; methods become $get/$post/...
const res = await client.posts.$post({ form: { title: 'Hello', body: 'Hono' } })
if (res.ok) console.log((await res.json()).message)
```

| Client feature | Usage |
| --- | --- |
| JSON body | `{ json: {...} }` |
| Form body | `{ form: {...} }` |
| Query params | `{ query: {...} }` — **values must be strings** (validators coerce) |
| Path params | `{ param: {...} }`; nested: `client.posts[':id'][':commentId'].$get({ param: { id: '123' } })` |
| Headers (per request) | second arg: `{ headers: { Authorization: 'Bearer x' } }` |
| Headers (client-wide) / cookies | `hc<AppType>(url, { headers: {...}, init: { credentials: 'include' } })` |
| Raw RequestInit (abort, etc.) | second arg `{ init: { signal } }` — `init` has highest priority |
| Type helpers | `InferResponseType<typeof client.posts.$get>` (add status: `, 200`), `InferRequestType<...>` |
| URL builders | `client.api.posts[':id'].$url({ param: { id: '123' } })` — **absolute base URL required**; `$path({ query })` works with relative bases and returns a string |

Note: `hc` does not URL-encode `param` values — plain `:param` segments never match slashes, so use `encodeURIComponent` or a regex route like `'/posts/:id{.+}'` on the server.

### Larger apps

Chain at every level, export the top-level chained type:

```ts
// authors.ts
const app = new Hono()
  .get('/', (c) => c.json('list authors'))
  .get('/:id', (c) => c.json(c.req.param('id')))
export default app

// index.ts
const routes = app.route('/authors', authors).route('/books', books)
export default app
export type AppType = typeof routes
```

### Known issues (RPC at scale)

- Big apps slow `tsserver` (type instantiation per route). Mitigations, best first: **compile the client and export a pre-typed client**:
  ```ts
  const client = hc<typeof app>('')
  export type Client = typeof client
  export const hcWithType = (...args: Parameters<typeof hc>): Client => hc<typeof app>(...args)
  ```
- Keep the Hono version identical in server and client packages (mismatches cause "Type instantiation is excessively deep").
- In monorepos, use TypeScript project references; split large apps into several `hc` clients.
- Handlers that return a `.then()` chain lose response types (client sees `unknown`) — use `async/await`.
- Requires `"strict": true` in both server and client tsconfigs.

## Testing

### `app.request()` — no extra deps

```ts
const res = await app.request('/posts', {
  method: 'POST',
  body: JSON.stringify({ message: 'hello hono' }),
  headers: new Headers({ 'Content-Type': 'application/json' }), // required for json validators!
})
expect(res.status).toBe(201)
```

Mock `c.env` (Workers bindings etc.) via the third argument:

```ts
const MOCK_ENV = { API_HOST: 'example.com', DB: { prepare: () => { /* mock */ } } }
const res = await app.request('/posts', {}, MOCK_ENV)
```

A `Request` instance works too: `await app.request(new Request('http://localhost/posts', { method: 'POST' }))`.

### `testClient()` — typed, RPC-style

```ts
import { testClient } from 'hono/testing'

const client = testClient(app)
const res = await client.search.$get({ query: { q: 'hono' } })
```

**Requirement:** routes must be chained on the instance (`new Hono().get(...)`) for type inference; separately-registered `app.get(...)` routes type as `unknown`. Second arg carries headers/init like `hc`.

For Cloudflare Workers, prefer `@cloudflare/vitest-pool-workers` with Vitest (Cloudflare's recommended integration).
