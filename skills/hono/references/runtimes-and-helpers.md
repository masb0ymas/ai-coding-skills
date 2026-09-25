# Hono Runtimes & Helpers

Source: https://hono.dev/docs/getting-started/, https://hono.dev/docs/helpers/

## Scaffold

```sh
npm create hono@latest my-app   # pick a template: cloudflare-workers, nodejs, bun, deno, vercel, aws-lambda, ...
```

Same app code everywhere; only the entry point differs.

## Entry points per runtime

| Runtime | Entry (`src/index.ts`) |
| --- | --- |
| Cloudflare Workers / Pages | `export default app` — dev with `wrangler dev` (port 8787), deploy with `npm run deploy` |
| Bun | `export default app` (existing project: `export default { port: 3000, fetch: app.fetch }`) |
| Deno | `Deno.serve(app.fetch)` (port option: `Deno.serve({ port: 8787 }, app.fetch)`) |
| Node.js (≥18.14.1) | `import { serve } from '@hono/node-server'; serve(app)` |
| AWS Lambda | `hono/lambda-edge`, `hono/aws-lambda` adapters |
| Service Worker | `fire()` from `hono/service-worker` (`app.fire()` is deprecated) |

Node.js owns its server lifecycle, so handle shutdown yourself:

```ts
const server = serve(app)
process.on('SIGTERM', () => server.close((err) => process.exit(err ? 1 : 0)))
```

## `hono/adapter` — portable env & runtime detection

```ts
import { env, getRuntimeKey } from 'hono/adapter'

app.get('/env', (c) => {
  const { NAME } = env<{ NAME: string }>(c) // wrangler vars / process.env / Bun.env / Deno.env ...
  return c.text(`${NAME} on ${getRuntimeKey()}`) // workerd | deno | bun | node | edge-light | fastly | other
})
```

`c.env` is the direct (Workers-style) accessor; `env(c)` normalizes across runtimes.

## `hono/factory` — typed building blocks

```ts
import { createFactory, createMiddleware } from 'hono/factory'

const factory = createFactory<{ Variables: { foo: string } }>({ defaultAppOptions: { strict: false } })
const app = factory.createApp()

const mw = factory.createMiddleware(async (c, next) => { c.set('foo', 'bar'); await next() })

// RoR-style handlers without losing inference — the sanctioned escape hatch
const handlers = factory.createHandlers(logger(), mw, (c) => c.json(c.var.foo))
app.get('/api', ...handlers)
```

Use `createMiddleware` for reusable standalone middleware. Prefer inline handlers (`app.get(path, handler)`) otherwise — see SKILL.md best practices.

## `hono/cookie`

```ts
import { getCookie, setCookie, deleteCookie, getSignedCookie, setSignedCookie } from 'hono/cookie'

setCookie(c, 'name', 'value', { path: '/', secure: true, httpOnly: true, domain: 'example.com', maxAge? })
const v = getCookie(c, 'name')        // or getCookie(c) for all
deleteCookie(c, 'name', { path: '/' })

// signed (HMAC SHA-256 via WebCrypto — async)
await setSignedCookie(c, 'name', 'value', secret)
const ok = await getSignedCookie(c, secret, 'name') // false = bad signature, undefined = absent/not signed
```

## `hono/jwt`

```ts
import { sign, verify, decode } from 'hono/jwt'

const token = await sign({ sub: 'user123', exp: Math.floor(Date.now() / 1000) + 300 }, secret) // default HS256
const payload = await verify(token, secret, 'HS256') // throws if invalid/expired
const claims = decode(token) // no verification
```

For route protection prefer the `jwt()` middleware (`hono/jwt`) — payload lands in `c.get('jwtPayload')`.

## `hono/streaming`

```ts
import { stream, streamText, streamSSE } from 'hono/streaming'

app.get('/sse', (c) =>
  streamSSE(c, async (s) => {
    let id = 0
    while (!s.aborted) {
      await s.writeSSE({ data: new Date().toISOString(), event: 'time-update', id: String(id++) })
      await s.sleep(1000)
    }
  }, (err) => console.error(err)) // optional error handler
)
```

`streamText` sets chunked `text/plain`; `s.onAbort(fn)` registers abort handling. Wrangler quirk: add `c.header('Content-Encoding', 'Identity')` if streaming doesn't flush in local dev.

## `hono/route` — route introspection (replaces deprecated `c.req.routePath`)

```ts
import { routePath, baseRoutePath, basePath, matchedRoutes } from 'hono/route'

app.get('/posts/:id', (c) => c.json({ path: routePath(c) })) // '/posts/:id'
```

## JSX / HTML

Hono ships its own JSX runtime (`hono/jsx`) — no React dependency; works server-side and client-side (`hono/jsx-dom`).

```tsx
/** @jsxImportSource hono/jsx */  // or tsconfig jsxImportSource
import { Hono } from 'hono'

const app = new Hono()
app.get('/', (c) => c.html(<h1>Hello!</h1>))
```

Layouts: set a renderer with `c.setRenderer()` (see Context reference) or the `jsxRenderer()` middleware. CSS-in-JS via `hono/css`. Docs: https://hono.dev/docs/guides/jsx

## Other helpers

| Helper | Import | Purpose |
| --- | --- | --- |
| ConnInfo | `hono/conninfo` | `getConnInfo(c)` — peer address (runtime-dependent) |
| Proxy | `hono/proxy` | `proxy()` — fetch-based reverse proxying with header handling |
| HTML | `hono/html` | `raw()`, `escapeToBuffer` — safe template interpolation |
| SSG | `hono/ssg` | `toSSG()` — generate static sites from routes |
| Dev | `hono/dev` | dev-only utilities (e.g. `importable` file serving) |
| WebSocket | `hono/ws` / `hono/deno` / `hono/bun` | `upgradeWebSocket()` per runtime |
| Accepts | `hono/accepts` | content negotiation helpers |
| Testing | `hono/testing` | `testClient()` — see RPC & Testing reference |
