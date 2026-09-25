# Hono Middleware

Source: https://hono.dev/docs/guides/middleware and https://hono.dev/docs/middleware/builtin/

## Rules

- A **middleware** is `async (c, next) => ...`. Call `await next()` and return nothing to continue the chain, **or** return a `Response` to short-circuit (nothing after it runs).
- Execution order = registration order, onion-style: code before `next()` runs in registration order; code after runs in reverse.
- **Never wrap `next()` in try/catch/finally**: Hono catches throws from handlers/middleware, routes them to `app.onError` (or a default 500), and unwinds normally — `next()` never throws.

```ts
app.use(async (c, next) => {          // global: matches all methods/paths
  console.log(`[${c.req.method}] ${c.req.url}`)
  await next()
})

app.use('/posts/*', cors())           // path-scoped
app.post('/posts/*', basicAuth())     // method + path
```

## Reusable middleware: `createMiddleware`

```ts
import { createMiddleware } from 'hono/factory'

const echoMiddleware = createMiddleware<{
  Variables: { echo: (str: string) => string }
}>(async (c, next) => {
  c.set('echo', (str) => str)
  await next()
})

app.get('/echo', echoMiddleware, (c) => c.text(c.var.echo('Hello!')))
```

- Factories taking arguments: `(opts: Opts) => createMiddleware(async (c, next) => ...)`.
- Chained `.use(a).use(b).get(handler)` types accumulate — the handler sees `Variables` from both middleware.

## Accessing context inside a middleware *factory call site*

To read `c.env` etc. when constructing a middleware inline, invoke it manually:

```ts
app.use('*', async (c, next) => {
  const middleware = cors({ origin: c.env.CORS_ORIGIN })
  return middleware(c, next)
})
```

## Built-in middleware catalog

All zero-dependency. Import path shown; register with `app.use(...)` **above** routes.

| Middleware | Import | Key usage |
| --- | --- | --- |
| Logger | `hono/logger` | `logger()`; custom logger via `logger(console)` |
| CORS | `hono/cors` | `cors({ origin, allowHeaders, allowMethods, exposeHeaders, maxAge, credentials })`; `origin` may be string, array, or function |
| Basic Auth | `hono/basic-auth` | `basicAuth({ username, password, hashFunction? })` |
| Bearer Auth | `hono/bearer-auth` | `bearerAuth({ token })` |
| JWT Auth | `hono/jwt` | `jwt({ secret, alg? })` — sets `c.get('jwtPayload')` |
| JWK | `hono/jwk` | `jwk({ jwks_uri })` — remote key-set verification |
| CSRF | `hono/csrf` | `csrf({ origin? })` — validates Origin/`Sec-Fetch-Site` |
| Secure Headers | `hono/secure-headers` | `secureHeaders()` — sets CSP, X-Frame-Options, etc.; pass `false` to suppress a header |
| ETag | `hono/etag` | `etag({ retainedHeaders? })` — weak/strong ETag + 304 |
| Compress | `hono/compress` | `compress({ contentTypeFilter? })` — CompressionStream; Node/Bun |
| Body Limit | `hono/body-limit` | `bodyLimit({ maxSize, onError? })` |
| Timeout | `hono/timeout` | `timeout(ms, exception?)` |
| Cache | `hono/cache` | `cache({ cacheName, wait? })` — uses Cache API (Workers/Deno/Bun), use `onCacheNotAvailable` elsewhere |
| Pretty JSON | `hono/pretty-json` | `prettyJSON({ space? })` |
| Request ID | `hono/request-id` | `requestId()` — reads/generates `c.get('requestId')` (via `X-Request-Id`) |
| Timing | `hono/timing` | `timing()` + `setMetric(c, name)` / `getMetric` — Server-Timing header |
| Trailing Slash | `hono/trailing-slash` | `appendTrailingSlash()` / `trimTrailingSlash()` |
| Method Override | `hono/method-override` | `methodOverride({ app, allowedMethods? })` — `_method` in form/query |
| Method Not Allowed | `hono/method-not-allowed` | `methodNotAllowed()` — 405 responses |
| IP Restriction | `hono/ip-restriction` | `ipRestriction(getConnInfo, { denyList, allowList })` — needs a runtime `getConnInfo` (e.g. `hono/bun`) |
| Combine | `hono/combine` | `some(...)` / `every(...)` / `except(...)` to compose middleware |
| JSX Renderer | `hono/jsx-renderer` | `jsxRenderer(Layout)` + `useRequestContext()` |
| Context Storage | `hono/context-storage` | `contextStorage()` — access `c` outside the handler chain (AsyncLocalStorage) |
| Powered By | `hono/powered-by` | `poweredBy()` — X-Powered-By: Hono (usually remove instead) |

Third-party middleware (GraphQL Server, Sentry, Firebase Auth, Zod Validator, …) lives in the `honojs/middleware` monorepo — see https://hono.dev/docs/middleware/third-party.

## Full CORS example (typical API setup)

```ts
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { prettyJSON } from 'hono/pretty-json'

const app = new Hono()

app.use(logger())
app.use('/api/*', cors({ origin: ['https://example.com'], allowHeaders: ['Authorization'] }))
app.use('/api/*', prettyJSON())

app.onError((err, c) => { /* see validation-and-errors.md */ })

const routes = app.route('/api', apiApp)
export default app
export type AppType = typeof routes
```
