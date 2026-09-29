# Better Auth — Server API & Hooks

Source: https://www.better-auth.com/docs/concepts/api, /docs/concepts/hooks

## Calling endpoints on the server

`auth.api` exposes every endpoint from core and every installed plugin. Arguments are a single object — `body`, `headers`, `query` — never positional.

```ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

await auth.api.getSession({ headers: await headers() });

await auth.api.signInEmail({
  body: { email, password },
  headers: await headers(),        // optional, but gives IP / user agent
});

await auth.api.verifyEmail({ query: { token: "my_token" } });
```

**Server calls throw on failure**; the client returns `{ data, error }`.

## Getting headers or a Response

```ts
// Headers (e.g. to read Set-Cookie)
const { headers: resHeaders, response } = await auth.api.signUpEmail({
  returnHeaders: true,
  body: { email, password, name },
});
const cookies = resHeaders.getSetCookie();

// Raw Response
const res = await auth.api.signInEmail({
  body: { email, password },
  asResponse: true,
});
```

## Error handling

```ts
import { APIError, isAPIError } from "better-auth/api";

try {
  await auth.api.signInEmail({ body: { email, password } });
} catch (error) {
  if (isAPIError(error)) {
    console.log(error.message, error.status, error.body);
  }
}
```

Error codes are also available on the client as `authClient.$ERROR_CODES` for translating messages.

## Hooks

Use hooks to customize an endpoint instead of building a parallel endpoint. `before` and `after` each accept **one** middleware — branch on `ctx.path` for multiple endpoints.

```ts
import { betterAuth } from "better-auth";
import { createAuthMiddleware, APIError } from "better-auth/api";

export const auth = betterAuth({
  hooks: {
    before: createAuthMiddleware(async (ctx) => {
      if (ctx.path !== "/sign-up/email") return;
      if (!ctx.body?.email.endsWith("@example.com")) {
        throw new APIError("BAD_REQUEST", { message: "Email must end with @example.com" });
      }
    }),
    after: createAuthMiddleware(async (ctx) => {
      if (ctx.path.startsWith("/sign-up")) {
        const newSession = ctx.context.newSession;
        if (newSession) await sendWelcome(newSession.user);
      }
    }),
  },
});
```

Modify the request from a `before` hook by returning a new context:

```ts
return { context: { ...ctx, body: { ...ctx.body, name: "John Doe" } } };
```

### `ctx` properties

`ctx.path`, `ctx.body` (POST), `ctx.headers`, `ctx.request` (may be absent for server-only endpoints), `ctx.query`, `ctx.context`.

### `ctx.context`

| Property | Meaning |
| --- | --- |
| `newSession` | Session created by this request — **after hooks only** |
| `returned` | Value returned by the previous hook/endpoint (success or `APIError`) |
| `responseHeaders` | Headers added so far |
| `authCookies` | e.g. `ctx.context.authCookies.sessionToken.name` |
| `secret` | The instance secret |
| `password.hash` / `password.verify` | The configured hasher |
| `adapter` / `internalAdapter` | Low-level and action-level DB access (`createUser`, `createSession`, …) |
| `generateId` | ID generator used by the instance |
| `runInBackground(promise)` | Fire-and-forget after the response is sent |
| `runInBackgroundOrAwait(promise)` | Defers when a handler is configured, otherwise awaits |

Prefer `internalAdapter` over the raw adapter when you want `databaseHooks` and secondary storage to apply.

Background tasks need a handler configured in `advanced.backgroundTasks`.

### Responding from a hook

```ts
return ctx.json({ message: "Hello World" });        // JSON response
throw ctx.redirect("/sign-up/name");                 // redirect
ctx.setCookie("my-cookie", "value");                 // cookies
await ctx.setSignedCookie("signed", "value", ctx.context.secret, { maxAge: 1000 });
const c = ctx.getCookie("my-cookie");
const s = await ctx.getSignedCookie("signed", ctx.context.secret);
throw new APIError("BAD_REQUEST", { message: "Invalid request" });
```

Hooks that need reuse across endpoints belong in a plugin instead.

## Type inference

```ts
type Session = typeof auth.$Infer.Session;          // { session, user }
type User = typeof auth.$Infer.Session.user;
type SessionRow = typeof auth.$Infer.Session.session;
```

Additional fields and plugin fields are inferred into these types automatically.

## Custom session response

`customSession` adds computed data (roles, org membership) to every session response. It runs on every fetch — session caching does not cache custom fields.

```ts
import { customSession } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    customSession(async ({ user, session }) => ({
      roles: await findUserRoles(session.userId),
      user: { ...user, newField: "x" },
      session,
    })),
  ],
});
```

To infer plugin-added fields inside the callback, build options first and pass them in:

```ts
const options = { /* ...config, plugins */ } satisfies BetterAuthOptions;
export const auth = betterAuth({
  ...options,
  plugins: [
    ...(options.plugins ?? []),
    customSession(async ({ user, session }) => ({ user, session }), options),
  ],
});
```

Client inference needs `customSessionClient<typeof auth>()`, which requires importing the server `auth` as a type — impossible across separate repos.
