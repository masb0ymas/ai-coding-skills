# Hono App & Routing

Source: https://hono.dev/docs/api/hono and https://hono.dev/docs/api/routing

## App methods

```ts
import { Hono } from 'hono'

const app = new Hono()

app.HTTP_METHOD([path,] handler | middleware...) // get/post/put/delete/query/...
app.all([path,] handler | middleware...)         // any HTTP method
app.on(method | method[], path | path[], handler | middleware...)
app.use([path,] middleware)
app.route(path, subApp)   // mount a Hono sub-app under a path
app.basePath(path)        // prefix for all routes of this instance
app.notFound(handler)
app.onError((err, c) => Response)
app.mount(path, otherHandler, { replaceRequest? }) // mount non-Hono apps (e.g. itty-router, Express)
app.request(path, init?, env?)   // testing: returns Response
app.fetch(request, env?, ctx?)   // the app is itself a fetch handler
```

Notes:

- `app.notFound` is only invoked from the **top-level** app; `notFound` set on a sub-app never fires.
- Route-level `onError` takes priority over the parent app's `onError`.
- `app.fire()` is **deprecated** (service-worker era). Export the app or wire `fetch` yourself.

## Path patterns

```ts
app.get('/user/:name', (c) => c.req.param('name'))            // single param
app.get('/posts/:id/comment/:commentId', (c) => c.req.param()) // all params at once
app.get('/api/animal/:type?', (c) => ...)                      // optional param
app.get('/post/:date{[0-9]+}/:title{[a-z]+}', (c) => ...)      // regex constraint
app.get('/posts/:filename{.+\\.png}', (c) => ...)              // param including slashes
app.get('/wild/*/card', (c) => ...)                            // wildcard segment
app.get('*', (c) => ...)                                       // match-all (fallback when last)
app.on(['PUT', 'DELETE'], '/post', (c) => ...)                 // multiple methods
app.on('GET', ['/hello', '/ja/hello'], (c) => ...)             // multiple paths
```

Regex path params are the way to match slashes inside one segment (plain `:param` never matches `/`).

## Chaining, grouping, base paths

```ts
// chained routes — required for RPC/testClient type inference
const app = new Hono()
  .get('/books', (c) => c.json('list'))
  .post('/books', (c) => c.json('create', 201))

// grouping: build a sub-app, then mount it
const book = new Hono()
book.get('/', (c) => c.text('List Books')) // GET /book once mounted
app.route('/book', book)

// base path on the instance itself
const api = new Hono().basePath('/api')
api.get('/book', (c) => c.text('List Books')) // GET /api/book
```

### Mount-order pitfall

`app.route(path, subApp)` copies whatever routes the sub-app has *at that moment*. This silently 404s:

```ts
three.get('/hi', (c) => c.text('hi'))
app.route('/two', two)   // two is still empty!
two.route('/three', three)
```

Register the innermost routes first, then mount outward (`three` → `two` → `app`).

## Routing priority

Handlers and middleware dispatch in **registration order**; the first handler that runs terminates the chain:

```ts
app.get('/book/a', (c) => c.text('a'))
app.get('/book/:slug', (c) => c.text('common'))
// GET /book/a -> 'a', GET /book/b -> 'common'

app.get('*', (c) => c.text('common')) // registered FIRST swallows /foo!
app.get('/foo', (c) => c.text('foo'))
```

Consequences:

- Middleware goes **above** the handlers it wraps (`app.use(logger())` before routes).
- A catch-all handler registered **below** real routes acts as a fallback.

## Hostname / header routing

Pass `getPath` to route by anything derivable from the request (e.g. hostname):

```ts
const app = new Hono({
  getPath: (req) =>
    '/' + req.headers.get('host') + req.url.replace(/^https?:\/\/[^/]+(\/[^?]*).*/, '$1'),
})
app.get('/www1.example.com/hello', (c) => c.text('hello www1'))
```

## App options

```ts
new Hono({ strict: false })                          // /hello == /hello/ (default: strict)
new Hono({ router: new RegExpRouter() })             // default: SmartRouter
new Hono({ getPath: (req) => ... })                  // custom routing key
new Hono<{ Bindings: B; Variables: V }>()            // Env typing
```

## Routers & presets

| Preset | Routers inside | Use for |
| --- | --- | --- |
| `hono` (default) | SmartRouter → RegExpRouter + TrieRouter | Most apps; long-lived servers (Node/Bun/Deno) and v8 isolates (Workers) |
| `hono/quick` | SmartRouter → LinearRouter + TrieRouter | Environments that re-init the app per request |
| `hono/tiny` | PatternRouter (~15KB total app) | Smallest footprint / limited resources |

Router facts: `RegExpRouter` compiles all routes into one big regex (fastest matching, but registration is slower and it doesn't support every pattern, hence the fallback pair); `TrieRouter` supports all patterns; `LinearRouter` has the fastest registration; `PatternRouter` is the smallest.
