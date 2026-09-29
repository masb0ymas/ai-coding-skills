# Better Auth — Framework Integrations

Source: https://www.better-auth.com/docs/installation, /docs/integrations/*

Every integration follows the same shape: expose `auth.handler` (a `(Request) => Promise<Response>`) on a catch-all route matching your `basePath` (default `/api/auth`). Register that route **before** body parsers and catch-all routes.

## Hono

No adapter needed — Hono and Better Auth both speak Web `Request`/`Response`.

```ts title="src/index.ts"
import { Hono } from "hono";
import { auth } from "./auth";

const app = new Hono();
app.all("/api/auth/*", (c) => auth.handler(c.req.raw));
export default app;
```

With a global basePath, mount at the remainder:

```ts
const app = new Hono().basePath("/api");
app.all("/auth/*", (c) => auth.handler(c.req.raw));
```

### CORS

```ts
import { cors } from "hono/cors";

app.use("/api/auth/*", cors({ origin: "http://localhost:3001", credentials: true }));
app.all("/api/auth/*", (c) => auth.handler(c.req.raw));
```

Add the same origin to `trustedOrigins` in `auth.ts`. With `credentials: true` never use `origin: "*"`.

### Session middleware

```ts
import { createMiddleware } from "hono/factory";
import { HTTPException } from "hono/http-exception";

type Env = { Variables: { session: typeof auth.$Infer.Session | null } };

export const sessionMiddleware = createMiddleware<Env>(async (c, next) => {
  const session = await auth.api.getSession({ headers: c.req.raw.headers });
  c.set("session", session);
  await next();
});

app.get("/hello", sessionMiddleware, (c) => {
  const session = c.get("session");
  if (!session) throw new HTTPException(401, { message: "Unauthorized" });
  return c.json({ user: session.user });
});
```

## Next.js

**App Router:**

```ts title="app/api/auth/[...all]/route.ts"
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

**Pages Router** — disable body parsing so Better Auth reads the raw stream:

```ts title="pages/api/auth/[...all].ts"
import { toNodeHandler } from "better-auth/node";
export const config = { api: { bodyParser: false } };
export default toNodeHandler(auth.handler);
```

Server components / actions:

```ts
import { headers } from "next/headers";
const session = await auth.api.getSession({ headers: await headers() });
```

**Server-action cookies:** server calls that set cookies need `nextCookies()`, added **last** in the `plugins` array, so Next's cookie store receives them.

```ts
import { nextCookies } from "better-auth/next-js";
export const auth = betterAuth({ plugins: [/* ...others */, nextCookies()] });
```

## Express / Node

```ts title="server.ts"
import express from "express";
import { toNodeHandler, fromNodeHeaders } from "better-auth/node";
import { auth } from "./auth";

const app = express();

app.all("/api/auth/*", toNodeHandler(auth));   // Express v5: "/api/auth/{*any}"
app.use(express.json());                        // body parser AFTER the auth handler

app.get("/api/me", async (req, res) => {
  const session = await auth.api.getSession({ headers: fromNodeHeaders(req.headers) });
  res.json(session);
});

app.listen(8000);
```

`fromNodeHeaders` converts Node's `IncomingHttpHeaders` into a web `Headers` — needed for every `auth.api` call in Node frameworks. CommonJS is not supported.

Fastify/Hapi follow the same pattern with their own raw-request bridging.

## SvelteKit

```ts title="src/hooks.server.ts"
import { auth } from "$lib/auth";
import { svelteKitHandler } from "better-auth/svelte-kit";
import { building } from "$app/environment";

export async function handle({ event, resolve }) {
  return svelteKitHandler({ event, resolve, auth, building });
}
```

Server actions that set cookies need `sveltekitCookies` (also exported from `better-auth/svelte-kit`), added last in the `plugins` array.

## Nuxt

```ts title="server/api/auth/[...all].ts"
import { auth } from "~~/lib/auth";

export default defineEventHandler((event) => auth.handler(toWebRequest(event)));
```

`toWebRequest` is auto-imported by Nitro (it comes from h3, **not** from `better-auth/node`).

## Astro

```ts title="src/pages/api/auth/[...all].ts"
import type { APIRoute } from "astro";
import { auth } from "@/auth";

export const GET: APIRoute = async (ctx) => auth.handler(ctx.request);
export const POST: APIRoute = async (ctx) => auth.handler(ctx.request);
```

## Elysia

```ts
const betterAuthView = (context: Context) => {
  const ALLOWED = ["POST", "GET"];
  if (ALLOWED.includes(context.request.method)) return auth.handler(context.request);
  context.error(405);
};

new Elysia().all("/api/auth/*", betterAuthView).listen(3000);
```

## TanStack Start

```ts title="src/routes/api/auth/$.ts"
export const Route = createFileRoute("/api/auth/$")({
  server: {
    handlers: {
      GET: async ({ request }) => auth.handler(request),
      POST: async ({ request }) => auth.handler(request),
    },
  },
});
```

Add `tanstackStartCookies()` (from `better-auth/tanstack-start`, or `/solid` for Solid) **last** in `plugins` so cookie-setting methods work.

## Expo / React Native

```ts title="app/api/auth/[...all]+api.ts"
import { auth } from "@/lib/server/auth";
const handler = auth.handler;
export { handler as GET, handler as POST };
```

Use `disableDefaultFetchPlugins: true` on the client (browser redirect plugins don't apply), and the `@better-auth/expo` plugin for secure credential storage.

## SolidStart

```ts
import { toSolidStartHandler } from "better-auth/solid-start";
export const { GET, POST } = toSolidStartHandler(auth);
```

## Cross-cutting

- **Cloudflare Workers:** add `compatibility_flags = ["nodejs_compat"]` (or `["nodejs_als"]`) — Better Auth needs `AsyncLocalStorage`.
- **Cookie-setting server calls** in Next.js, SvelteKit, and TanStack Start require the respective cookies plugin, always last in the `plugins` array.
- **Cross-origin frontends** need both CORS middleware (with `credentials: true`) and matching `trustedOrigins`; see the Sessions & Cookies reference for Safari/ITP and cross-subdomain setup.
