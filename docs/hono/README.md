# Hono

Hono is a small, fast web framework built entirely on Web Standard APIs — `Request`, `Response`, and `fetch` ([hono.dev](https://hono.dev), repo [honojs/hono](https://github.com/honojs/hono)). The same application code runs unchanged on Cloudflare Workers, Node.js, Bun, Deno, AWS Lambda, Vercel, Netlify, and Fastly; only the entry point differs. This skill is a condensed snapshot of the official docs, written for this repository and verified against **Hono v4.13** by typechecking every documented pattern against the real package.

## When to use it

- The user mentions Hono or hono.dev.
- Code imports from `hono`, `hono/client`, `hono/factory`, `hono/adapter`, `hono/cors`, `hono/jwt`, `hono/validator`, or any other `hono/*` subpath.
- Creating routes or handlers, writing custom middleware, or using the built-in middleware catalog.
- Reading request data or building responses through `Context` (`c.req`, `c.json`, `c.env`, `c.set`).
- Validating input with `validator()` or `@hono/zod-validator`, or handling errors with `HTTPException` and `app.onError`.
- Setting up typed RPC between server and client with `hc` and `AppType`, or testing with `app.request()` and `testClient`.
- Choosing an entry point for a specific runtime, or deploying to an edge/serverless platform.
- Not for: other web frameworks. The skill does not guess option lists for a middleware or helper that its references do not cover — it fetches the live page instead.

## What it covers

### Core model

Handlers are functions that take a `Context` and return a `Response`; exactly one handler runs per request. Middleware is an `async (c, next)` function that does work, calls `await next()`, and may modify the response afterwards — an onion model where code before `next()` runs before the handler and code after runs after it. A middleware that returns a `Response` instead of calling `next()` short-circuits the chain.

### Best practices from the official guide

- **Write handlers inline after the path** rather than extracting controllers — path params, validated values, and response types are only inferred when the handler is attached to the route directly. For shared handlers, use `factory.createHandlers()`.
- **Chain routes** (`new Hono().get(...).post(...)`) when using RPC or `testClient`, because route types only survive the chain.
- **Structure large apps with `app.route()`**, mounting sub-apps rather than building controller layers.
- **Registration order is execution order** — middleware must be registered above the handlers it wraps, and a `app.get('*', ...)` registered first will swallow everything below it.
- **`app.route()` copies routes at call time**, so a sub-app populated after mounting silently 404s.
- **Never wrap `next()` in try/catch** — Hono catches throws and routes them to `app.onError` before unwinding.
- **No dedicated HEAD handlers** — Hono converts HEAD to GET and strips the body before matching.
- **Trailing slashes are distinct** unless you pass `{ strict: false }`.
- **Prefer small `Env` generics** (`new Hono<{ Bindings, Variables }>()`) over global `ContextVariableMap` augmentation.

### Reference areas

| Area | What it covers |
| --- | --- |
| App & routing | App methods, path params, grouping, `route()`/`basePath()`, routing priority, routers and presets, strict mode, `mount()` |
| Context & request | `c.json/text/html`, `c.set/get/var`, `c.env`, `c.req.param/query/header/parseBody`, renderers |
| Middleware | Writing custom middleware, execution order, and the full built-in catalog with imports |
| Validation & errors | `validator()`, `zValidator`, Standard Schema, `HTTPException`, `app.onError`/`notFound` |
| RPC & testing | `hc` client, `AppType`, `$url()`/`$path()`, monorepo tips, `app.request()`, `testClient` |
| Runtimes & helpers | Entry points per runtime, env via `hono/adapter`, `hono/factory`, cookie, JWT, streaming/SSE |

## How it works

The skill is a task-routed reference set. The agent reads the reference that matches the task (per the routing table in `SKILL.md`) before writing non-trivial code in that area, keeps handlers inline so type inference survives, chains routes when the project uses RPC or `testClient`, and fetches the live page for exact option lists of a specific middleware or helper rather than trusting memory.

## Files

- `SKILL.md` — entry point: core model, the official best-practices list, the minimal API surface for `app`, `Context`, and `c.req`, and live-doc links.
- `references/app-and-routing.md` — app methods, path params, grouping, `route()`/`basePath()`, routing priority, routers and presets, strict mode, `mount()`.
- `references/context-and-request.md` — response helpers, `c.set/get/var`, `c.env`, request accessors, renderers.
- `references/middleware.md` — custom middleware, execution order, `createMiddleware`, and the built-in middleware catalog.
- `references/validation-and-errors.md` — `validator()`, `zValidator`, Standard Schema, `HTTPException`, `app.onError`, `notFound`.
- `references/rpc-and-testing.md` — `hc` client, `AppType`, `$url()`/`$path()`, monorepo patterns, `app.request()`, `testClient`.
- `references/runtimes-and-helpers.md` — per-runtime entry points, `hono/adapter`, `hono/factory`, cookie, JWT, streaming and SSE.

## Example prompts

```text
Create a Hono API with CRUD routes for posts, Zod validation, and an onError handler.
```

```text
Set up typed RPC between my Hono backend and a React frontend using hc.
```

```text
Add JWT auth middleware to my Hono app and write tests with testClient.
```

```text
Deploy this Hono app to Cloudflare Workers — show the entry point and wrangler config.
```

## Install

```sh
./install.sh --target claude --skill hono /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

The guidance was authored for this repository and condenses the official Hono documentation ([hono.dev/docs](https://hono.dev/docs); docs markdown lives in [honojs/website](https://github.com/honojs/website) under `docs/`). No LICENSE file is bundled with this skill.
