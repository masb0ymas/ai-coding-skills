---
name: better-auth
description: Best practices and API reference for Better Auth (better-auth.com), the framework-agnostic TypeScript authentication and authorization library. Use when setting up auth (email/password, social/OAuth providers, magic link, OTP, passkey, anonymous, SSO/SAML), creating a betterAuth() instance, mounting auth handlers in Next.js/Hono/Express/SvelteKit/Nuxt/Astro/Expo, calling auth.api on the server, using the authClient on the client, managing sessions and cookies (cookie cache, stateless mode, cross-subdomain), configuring database adapters (Drizzle, Prisma, MongoDB, Kysely, SQLite, Postgres, MySQL) or the CLI (generate/migrate/check/create-admin), adding plugins (twoFactor, admin, organization, jwt, apiKey, bearer, username, phoneNumber, multiSession, oauthProvider), extending the schema with additionalFields, writing hooks or custom plugins, or debugging Better Auth errors and CSRF/origin/rate-limit issues. Trigger whenever code imports from "better-auth" or any "@better-auth/*" package, or the user mentions Better Auth, betterAuth, authClient, or better-auth plugins, even if they don't say "best practices".
---

# Better Auth

Better Auth is a framework-agnostic TypeScript auth library. One `betterAuth()` server instance owns the schema, sessions, and every endpoint; a separate `createAuthClient()` on the frontend calls those endpoints. Built-in email/password + social providers, 50+ official plugins, and an adapter layer over Kysely, Drizzle, Prisma, and MongoDB.

This skill is a condensed snapshot of the official docs (Better Auth v1.7, verified September 2026 against the real package). Import paths and plugin packaging changed in v1.7 — several plugins moved to separate `@better-auth/*` packages. Where a detail is version-sensitive, the reference links the live page.

## References

| Area | Resource | When to Use |
| --- | --- | --- |
| Setup & Config | `references/setup-and-config.md` | Install, `betterAuth()` instance, `baseURL`/`trustedOrigins`/`secret`/`advanced`, rate limit, logging, CLI commands, TypeScript config |
| Database | `references/database.md` | Adapters (Kysely/Drizzle/Prisma/Mongo), core schema, `additionalFields`, ID generation, `databaseHooks`, secondary storage, migrations, joins |
| Sessions & Cookies | `references/sessions-and-cookies.md` | Session lifecycle, `expiresIn`/`updateAge`/`freshAge`, cookie cache strategies, stateless mode, session management API, cookie/cross-subdomain config, Safari ITP |
| Authentication | `references/authentication.md` | Email & password, email verification, password reset, social/OAuth providers, account linking & unlinking, user management (update/change email/delete) |
| Server API & Hooks | `references/server-api-and-hooks.md` | `auth.api.*` calls, `body`/`headers`/`query`/`asResponse`/`returnHeaders`, `APIError`, `hooks.before/after`, `ctx.context`, type inference |
| Client | `references/client.md` | `createAuthClient()` per framework, methods, `useSession`, fetch options, error codes, SSR hydration, client plugins |
| Plugins | `references/plugins.md` | Full plugin catalog with correct import paths, 2FA/admin/organization/jwt/apiKey usage, writing custom server + client plugins |
| Integrations | `references/integrations.md` | Mounting handlers in Hono, Next.js, Express/Fastify, SvelteKit, Nuxt, Astro, Elysia, TanStack Start, Expo; CORS; session middleware |

Read the relevant reference before writing non-trivial code in that area. The essentials are below.

## Setup non-negotiables

```sh
npm install better-auth          # client + server (install in both if separate projects)
npx auth@latest secret           # generate BETTER_AUTH_SECRET (32+ chars, high entropy)
```

```txt title=".env"
BETTER_AUTH_SECRET=...
BETTER_AUTH_URL=http://localhost:3000
```

1. **Always set `baseURL` explicitly** (config or `BETTER_AUTH_URL`). Request inference is not recommended for security/stability.
2. **Put the auth instance in `auth.ts`** at the project root, `lib/`, `utils/`, or any of those under `src/`/`app/`/`server/`. Export it as `auth` or default — the CLI finds it there.
3. **Mount the handler at `/api/auth/*`** (the default `basePath`), before any catch-all route.
4. **Run `npx auth@latest generate`** (or `migrate` with the built-in Kysely adapter) to create the schema. Add plugin tables the same way.

```ts title="auth.ts"
import { betterAuth } from "better-auth";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool(),
  emailAndPassword: { enabled: true },
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID as string,
      clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
    },
  },
});
```

```ts title="src/index.ts — Hono mount (raw Web Request in, Response out)"
import { Hono } from "hono";
import { auth } from "./auth";

const app = new Hono();
app.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));
export default app;
```

```ts title="auth-client.ts — separate file from the server instance"
import { createAuthClient } from "better-auth/react"; // or /client, /vue, /svelte, /solid
export const authClient = createAuthClient({ baseURL: "http://localhost:3000" });
```

## Rules that prevent most Better Auth bugs

**Never call client methods on the server.** `authClient.*` is browser-side. On the server use `auth.api.*`, which takes `{ body, headers, query }` as one object — not positional args.

**Server calls need headers for anything session-scoped.** `await auth.api.getSession({ headers: await headers() })`. Without headers there is no session, no IP, no user agent.

**`auth.api.*` throws; the client returns `{ data, error }`.** Wrap server calls in try/catch and check `isAPIError(error)` from `better-auth/api`. Client code checks `error` — it never throws.

**Several plugins are separate packages in v1.7+.** `passkey`, `apiKey`, `sso`, `scim`, `oauthProvider`, `cimd`, `i18n`, `stripe`, `mcp`, `agentAuth` install as `@better-auth/<name>` and import from there — not from `better-auth/plugins`. See the Plugins reference for the verified list.

**Guard `ctx` in `databaseHooks.user.update.before`.** Its second argument is `ctx | null` under `strict`; docs examples that read `ctx.context.session` unguarded do not typecheck.

**`ctx.context.session` is `{ session, user }`, not a session row.** Use `ctx.context.session.user.id` and `ctx.context.session.session.token`. For `databaseHooks`, the entity itself is the first argument.

**Enable both server and client plugins for client-callable features.** Adding `twoFactor()` on the server does not create `authClient.twoFactor.*`; you must also add `twoFactorClient()` to `createAuthClient`.

**An untyped client plugin breaks inference for every other plugin.** A `BetterAuthClientPlugin` without `$InferServerPlugin` collapses sibling plugin types to a stub — `authClient.admin.listUsers` silently stops existing. Give every client plugin a real `$InferServerPlugin`.

**Account selectors are `accountId`, never `providerId`.** `getAccessToken`, `refreshToken`, and `accountInfo` require the Better Auth account row `id` (from `listAccounts`) or `useAccountCookie: true`. `providerId` is not a selector.

**Don't await email sending in `sendVerificationEmail`/`sendResetPassword`.** Use `void sendEmail(...)` (or `waitUntil` on serverless) to avoid timing attacks.

**Enable email enumeration protection deliberately.** With `requireEmailVerification: true` or `autoSignIn: false`, sign-up returns 200 for existing emails. With the default config it still returns 422.

**Rate limiting is on in production, off in development by default.** Set `rateLimit.enabled` explicitly if you need it in dev or want it off in prod.

**`npx auth migrate` only works with the built-in Kysely adapter.** With Drizzle/Prisma use `generate` plus your ORM's migration tool.

## Verified API surface (v1.7.6)

`auth` (server): `handler`, `api.*`, `$Infer.Session`, `options`. Helpers: `toNodeHandler`/`fromNodeHeaders` (`better-auth/node`), `toNextJsHandler`/`nextCookies` (`better-auth/next-js`), `svelteKitHandler` (`better-auth/svelte-kit`), `toSolidStartHandler` (`better-auth/solid-start`), `tanstackStartCookies` (`better-auth/tanstack-start`), `getMigrations` (`better-auth/db/migration`), `getAccountCookie` (`better-auth/cookies`), `APIError`/`isAPIError`/`createAuthMiddleware` (`better-auth/api`), `betterAuth` from `better-auth/minimal` for smaller bundles with an adapter.

`authClient`: `signUp.email`, `signIn.email/social/username/sso/magicLink`, `signOut`, `getSession`, `useSession`, `hydrateSession`, `listSessions`, `revokeSession(s)/revokeOtherSessions`, `updateSession`, `updateUser`, `changeEmail`, `changePassword`, `requestPasswordReset`, `resetPassword`, `sendVerificationEmail`, `deleteUser`, `listAccounts`, `linkSocial`, `unlinkAccount`, `getAccessToken`, `$Infer.Session`, `$ERROR_CODES`, plus one namespace per installed plugin.

## Official AI resources

Better Auth ships its own agent resources — prefer them when this snapshot is not enough:
- Docs MCP server: `https://mcp.better-auth.com/mcp`
- `https://www.better-auth.com/llms.txt`
- Official skill pack: `npx skills add better-auth/skills` (repo `better-auth/skills`)

## Verify against live docs when precision matters

| Topic | Page |
| --- | --- |
| Installation | https://www.better-auth.com/docs/installation |
| Basic usage | https://www.better-auth.com/docs/basic-usage |
| Options reference | https://www.better-auth.com/docs/reference/options |
| Database | https://www.better-auth.com/docs/concepts/database |
| Session management | https://www.better-auth.com/docs/concepts/session-management |
| Hooks | https://www.better-auth.com/docs/concepts/hooks |
| Plugins | https://www.better-auth.com/docs/plugins |
| Security | https://www.better-auth.com/docs/reference/security |
| CLI | https://www.better-auth.com/docs/concepts/cli |
| Errors | https://www.better-auth.com/docs/reference/errors |
