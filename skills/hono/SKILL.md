---
name: hono
description: Best practices and API reference for building web apps and APIs with Hono (hono.dev), the web-standard TypeScript framework that runs on Cloudflare Workers, Node.js, Bun, Deno, and edge/serverless platforms. Use when creating Hono apps or routes, writing handlers or middleware, using Context (c.req, c.json, c.env, c.set), validation (@hono/zod-validator, hono/validator), RPC (hono/client hc), built-in middleware (JWT, CORS, basic auth, etag, compress), testing with app.request/testClient, or deploying to any runtime. Trigger whenever code imports from 'hono' or the user mentions Hono, even if they don't say "best practices".
---

# Hono

Hono is a small, fast web framework built entirely on Web Standard APIs (`Request`/`Response`/`fetch`). The same app code runs on Cloudflare Workers, Node.js, Bun, Deno, AWS Lambda, Vercel, Netlify, Fastly, and more — only the entry point differs.

This skill is a condensed snapshot of the official docs (Hono v4.13, verified September 2026). For exact option lists of a specific middleware or helper, fetch the live page linked in each reference file instead of trusting memory.

## References

| Area | Resource | When to Use |
| --- | --- | --- |
| App & Routing | `references/app-and-routing.md` | App methods, path params, grouping, `route()`/`basePath()`, routing priority, routers & presets, strict mode, `mount()` |
| Context & Request | `references/context-and-request.md` | `c.json/text/html`, `c.set/get/var`, `c.env`, `c.req.param/query/header/parseBody`, renderers |
| Middleware | `references/middleware.md` | Writing custom middleware, execution order, full catalog of built-in middleware with imports |
| Validation & Errors | `references/validation-and-errors.md` | `validator()`, `zValidator`, Standard Schema, `HTTPException`, `app.onError`/`notFound` |
| RPC & Testing | `references/rpc-and-testing.md` | `hc` client, `AppType`, `$url()`/`$path()`, monorepo tips, `app.request()`, `testClient` |
| Runtimes & Helpers | `references/runtimes-and-helpers.md` | Entry points per runtime, env via `hono/adapter`, `hono/factory`, cookie, JWT, streaming/SSE |

Read the relevant reference before writing non-trivial code in that area. The essentials that apply to nearly every task are below.

## Core model

- **Handler** — a function that takes `Context` and returns a `Response` (via `c.json()`, `c.text()`, …). Exactly one handler runs per request.
- **Middleware** — an `async` function that does work, calls `await next()`, and may touch the response afterwards. Think onion: code before `next()` runs before the handler, code after runs after.
- A middleware that returns a `Response` (instead of calling `next()`) short-circuits the chain.

```ts
import { Hono } from 'hono'

const app = new Hono()

app.use(async (c, next) => {          // middleware: runs first
  const start = performance.now()
  await next()
  c.res.headers.set('X-Response-Time', `${performance.now() - start}`)
})

app.get('/hello/:name', (c) => {      // handler
  const { name } = c.req.param()      // typed path params
  return c.json({ hello: name })
})

export default app // Workers/Bun entry; see Runtimes ref for Node/Deno
```

## Best practices (from the official guide)

**Write handlers inline after the path — don't extract "controllers".** Path params, validated values, and JSON response types are only inferred when the handler is attached to the route directly. If you must share handlers, use `factory.createHandlers()` from `hono/factory` (see Runtimes & Helpers ref).

**Chain routes when you use RPC or `testClient`.** `const app = new Hono().get(...).post(...)` preserves route types through the chain; separate `app.get(...)` statements do not. Required for `testClient` to be typed.

**Structure large apps with `app.route()`, not controllers.**

```ts
// authors.ts — export a Hono instance
const app = new Hono().get('/', (c) => c.json('list authors'))
export default app

// index.ts — mount it
app.route('/authors', authors)
```

**Registration order is execution order.** Middleware must be registered *above* the handlers it should wrap; a `app.get('*', ...)` handler registered first will swallow everything below it (use it *below* real routes as a fallback).

**`app.route()` copies routes at call time.** Mounting an empty sub-app and populating it afterwards silently 404s. Register the sub-app's routes before calling `.route()` on it.

**Never wrap `next()` in try/catch.** Hono catches handler/middleware throws and routes them to `app.onError` (or a default 500) before unwinding, so `next()` never throws.

**No dedicated HEAD handlers.** Hono converts HEAD to GET and strips the body before route matching — `app.head(...)` handlers are never called. Use GET routes; skip expensive body work in middleware when `c.req.method === 'HEAD'`.

**Trailing slashes are distinct by default.** `/hello` ≠ `/hello/` unless you pass `{ strict: false }` (or use the trailing-slash middleware).

**Small `Env` generics beat globals.** Type bindings and variables per app: `new Hono<{ Bindings: {...}; Variables: {...} }>()`. Prefer per-app `Variables` over `ContextVariableMap` augmentation — the latter claims types even where the middleware never ran.

## Minimal API surface

`app` methods: `get/post/put/delete/...([path,] handler|middleware...)`, `all()`, `on(method|methods, path|paths, handler)`, `use([path,] middleware)`, `route(path, app)`, `basePath(path)`, `notFound(handler)`, `onError(handler)`, `mount(path, otherApp)`, `request(path, init?, env?)` (testing), `fetch(request, env?, ctx?)`.

`Context` (`c`): responses `c.json()/c.text()/c.html()/c.body()/c.redirect()/c.notFound()`, `c.status(201)`, `c.header('X', 'y')`, `c.res`, request `c.req.*`, storage `c.set()/c.get()/c.var`, runtime `c.env` (bindings/env vars), `c.executionCtx`, error `c.error`.

`c.req`: `param('id')`, `query('q')`, `queries('tags')`, `header('X-Foo')`, `json()`, `text()`, `formData()`, `parseBody()` (form/multipart), `valid('json')` (validated values), `path`, `url`, `method`, `raw`.

## Verify against live docs when precision matters

| Topic | Page |
| --- | --- |
| Best practices | https://hono.dev/docs/guides/best-practices |
| App API | https://hono.dev/docs/api/hono |
| Routing | https://hono.dev/docs/api/routing |
| Context | https://hono.dev/docs/api/context |
| Middleware list | https://hono.dev/docs/middleware/builtin/ |
| RPC | https://hono.dev/docs/guides/rpc |
| Helpers | https://hono.dev/docs/helpers/ |
