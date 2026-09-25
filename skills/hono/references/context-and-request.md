# Hono Context & HonoRequest

Source: https://hono.dev/docs/api/context and https://hono.dev/docs/api/request

## Context (`c`) — responses

| Method | Notes |
| --- | --- |
| `c.text(body, status?, headers?)` | `Content-Type: text/plain` |
| `c.json(obj, status?, headers?)` | `Content-Type: application/json`; explicit status (200/404/…) is also what makes RPC responses typed per status |
| `c.html(html)` | `Content-Type: text/html` |
| `c.body(body, status?, headers?)` | raw body; prefer `c.text()`/`c.html()` when applicable |
| `c.redirect(location, status?)` | default 302 |
| `c.notFound()` | returns 404 (customizable via `app.notFound`) |
| `c.status(201)` | set before returning; only needed for non-200 |
| `c.header('X-Message', 'msg')` | sets response header; can be passed as third arg of `c.json/text` instead |
| `c.res` | the `Response` object; middleware may read/replace it **after** `next()` (`c.res = new Response(...)`) |

## Context — per-request storage

```ts
// type-safe: declare Variables on the app
const app = new Hono<{ Variables: { message: string } }>()

app.use(async (c, next) => {
  c.set('message', 'Hono is cool!!')
  await next()
})

app.get('/', (c) => c.text(c.get('message'))) // or c.var.message
```

- Values live for the current request only — never shared across requests.
- `c.var.message` is the accessor form; typed middleware that *provides* values uses `createMiddleware<{ Variables: {...} }>()` from `hono/factory`.
- Chaining `.use(mw1).use(mw2).get(...)` accumulates `Variables` types automatically — handlers see every variable set earlier in the chain.
- Avoid `declare module 'hono' { interface ContextVariableMap { ... } }` unless the variable is truly app-wide: it types `c.get('key')` as present **even in routes where the middleware never ran**.

## Context — runtime access

```ts
// Cloudflare Workers bindings (env vars, KV, D1, R2) — also used for Node process.env via hono/adapter
const val = await c.env.MY_KV.get('my-key')

// Workers-only execution context
c.executionCtx.waitUntil(c.env.KV.put(key, data))

// error set when the handler threw — inspect in middleware after next()
if (c.error) { ... }
```

## Renderers (layouts)

```ts
app.use(async (c, next) => {
  c.setRenderer((content) => c.html(<html><body><p>{content}</p></body></html>))
  await next()
})
app.get('/', (c) => c.render('Hello!')) // wrapped in the layout
```

Augment `ContextRenderer` to add typed extra args (e.g. `head: { title: string }`).

## HonoRequest (`c.req`)

### Path params / query / headers

```ts
c.req.param('id')        // typed; c.req.param() for all as object
c.req.query('q')         // single value; c.req.query() for all
c.req.queries('tags')    // string[] for repeated keys (?tags=A&tags=B)
c.req.header('User-Agent')
```

**Gotcha:** `c.req.header()` with no argument returns **lowercased** keys. Access specific headers by name: `c.req.header('X-Foo')` — not `c.req.header()['X-Foo']`.

### Body parsing

| Call | For |
| --- | --- |
| `await c.req.json()` | `application/json` |
| `await c.req.text()` | `text/plain` |
| `await c.req.arrayBuffer()` / `c.req.blob()` / `c.req.formData()` | raw / binary / standard FormData |
| `await c.req.parseBody()` | form/multipart convenience (see below) |

`parseBody()` details: `body['foo']` is `string | File` (last file wins); `body['foo[]']` is always `(string | File)[]`; option `{ all: true }` makes repeated names arrays without the `[]` suffix; option `{ dot: true }` structures `obj.key1` fields into `{ obj: { key1: ... } }`.

### Validated values & metadata

```ts
const { title } = c.req.valid('json') // targets: json | form | query | header | cookie | param
```

- `c.req.path` (pathname), `c.req.url` (full URL), `c.req.method`, `c.req.raw` (the standard `Request`).
- `cloneRawRequest(c.req)` from `hono/request` re-creates the raw Request even after the body was consumed by a validator.
- `c.req.routePath` / `c.req.matchedRoutes` are **deprecated since v4.8.0** — use the route helper `routePath(c)` / `matchedRoutes(c)` from `hono/route` instead.
