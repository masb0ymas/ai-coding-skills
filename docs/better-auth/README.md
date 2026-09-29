# Better Auth

Better Auth is a framework-agnostic, universal authentication and authorization framework for TypeScript ([better-auth.com](https://www.better-auth.com), repo [better-auth/better-auth](https://github.com/better-auth/better-auth)). It solves the problem of assembling auth from scratch in a TypeScript app by owning the whole stack: a `betterAuth()` server instance that generates the database schema, runs every auth endpoint, and manages sessions, plus a separate `createAuthClient()` for the frontend that calls those endpoints with full type inference. Built-in email/password and social providers ship with 50+ official plugins (2FA, passkeys, organizations, SSO, API keys, payments), and an adapter layer over Kysely, Drizzle, Prisma, and MongoDB.

This skill is a condensed snapshot of the official docs, written for this repository and verified against Better Auth **v1.7.6** by typechecking every documented pattern against the real packages in a temporary project. It documents the verified API surface, the import paths that changed in v1.7, and the places where the docs and the package disagree.

## When to use it

- The user mentions Better Auth, `betterAuth`, `authClient`, `auth.api`, or better-auth plugins.
- Code imports from `better-auth`, `better-auth/client`, `better-auth/plugins`, or any `@better-auth/*` package.
- Setting up auth: creating the instance, choosing a database adapter, mounting the handler, generating the schema.
- Adding an auth method: email/password, social/OAuth providers, magic link, email OTP, passkey, username, phone number, anonymous, SSO/SAML, generic OAuth.
- Working with sessions: expiration, freshness, cookie cache, stateless mode, cross-subdomain cookies, session revocation, Safari/ITP problems.
- Calling `auth.api.*` on the server or `authClient.*` in the browser, or wiring session middleware into a framework.
- Adding or configuring plugins, extending the schema with `additionalFields`, writing hooks, or authoring a custom server/client plugin.
- Debugging Better Auth errors, CSRF/origin rejections, rate limiting, or account-linking behavior.
- Not for: other auth libraries (Auth.js/NextAuth, Clerk, Lucia, Authula). The skill does not guess plugin options or endpoint names that are missing from its references — it fetches the live page instead.

## What it covers

### Verified against the real package

Every code pattern in the skill was typechecked against `better-auth@1.7.6` plus the separate `@better-auth/*` packages in a temp project with `strict: true`. That process surfaced several places where the documentation and the shipped types disagree, and the skill documents the correct form:

| Docs say | Reality in v1.7.6 |
| --- | --- |
| `passkey`, `apiKey` from `better-auth/plugins` | Separate packages: `@better-auth/passkey`, `@better-auth/api-key` (also `sso`, `scim`, `oauthProvider`, `cimd`, `i18n`, `stripe`, `mcp`, `agentAuth`) |
| `auth.api.linkSocial(...)` | `auth.api.linkSocialAccount(...)`; `linkSocial` is the client method |
| `authClient.twoFactor.verifyTOTP(...)` | `authClient.twoFactor.verifyTotp(...)` — the docs are inconsistent even within one page |
| `authClient.username.isUsernameAvailable(...)` | No `authClient.username` namespace; use `signIn.username` / `signUp.email({ username })` |
| `getAccessToken({ providerId })` | `getAccessToken({ accountId })` or `{ useAccountCookie: true }` — `providerId` is not a selector |
| `ctx.context.session.userId` in `databaseHooks` | `ctx` is nullable under strict; `ctx.context.session` is `{ session, user }` |
| Any client plugin without `$InferServerPlugin` | Silently collapses type inference for **all** sibling plugins |

### Setup and configuration

`betterAuth()` instance, the `auth.ts` locations the CLI searches, `baseURL` (static and multi-host object form), `trustedOrigins` wildcard syntax (`?`, `*`, `**`), `secret` and secret rotation, `advanced` (cookie prefix, secure cookies, cross-subdomain, ID generation, joins, schema validation, CSRF toggles), rate limiting, logging, telemetry, and the full CLI (`generate`, `migrate`, `check schema`, `create-admin`, `init`, `upgrade`, `info`, `secret`).

### Database

Adapters (built-in Kysely with a driver, Drizzle, Prisma, MongoDB), the four core tables and their exact fields, custom table/column names, extending the schema with `additionalFields` (including the `input`/`returned` matrix and the `role`-must-be-`input: false` trap), ID generation strategies (`false`, `"serial"`, `"uuid"`, callbacks for mixed types), `databaseHooks`, the secondary storage interface with the official Redis package, migrations including programmatic `getMigrations` for Cloudflare D1, schema validation, and joins.

### Sessions and cookies

Expiration/refresh/freshness, `deferSessionRefresh` for read replicas, cookie cache with the three strategies (`compact`, `jwt`, `jwe`) and the revocation caveat, JWKS-backed cookie-cache JWTs, the full session management API, stateless sessions with `refreshCache` and version-based invalidation, cookie names and attributes, cross-subdomain configuration, Safari ITP workarounds, and the security behaviors around CSRF, OAuth state/PKCE, and IP headers.

### Authentication methods

Email and password configuration, sign-up/sign-in flows, email verification (including enumeration protection and `customSyntheticUser`), password reset, social providers and their per-provider options, account linking and unlinking, user management (update, change email, change password, set/verify password), user deletion with its authentication requirements, and `validateUserInfo` as the central identity policy gate.

### Server API, hooks, and the client

`auth.api.*` calling conventions (`body`/`headers`/`query`, `asResponse`, `returnHeaders`), `APIError` handling, `hooks.before`/`hooks.after` with the full `ctx` and `ctx.context` surface (including `runInBackground`), type inference via `$Infer`, `customSession`, the client instance per framework, `useSession` in React/Vue/Svelte/Solid/vanilla, fetch options, error codes, SSR hydration, and client plugin authoring.

### Plugins

The complete catalog split into built-in (`better-auth/plugins`) and separate-package plugins, with correct import paths and client subpaths for each. Detailed coverage of 2FA, admin, organization, JWT, API key, bearer, username, and passkey, plus the plugin authoring APIs for both server (`createAuthEndpoint`, schema, hooks, middleware, rate limits, `BetterAuthPluginRegistry`) and client (`$InferServerPlugin`, `getActions`, `getAtoms`, `pathMethods`).

### Framework integrations

Mounting the handler in Hono, Next.js (App and Pages Router, plus `nextCookies`), Express/Node (`toNodeHandler`, `fromNodeHeaders`, Express v5 wildcard syntax), SvelteKit, Nuxt, Astro, Elysia, TanStack Start, Expo/React Native, and SolidStart, with CORS setup, session middleware, and the Cloudflare Workers `nodejs_compat` requirement.

## How it works

The skill is a task-routed reference set rather than a linear workflow. The agent:

1. **Reads the reference that matches the task**, per the routing table in `SKILL.md`, rather than loading everything.
2. **Puts the auth instance and the auth client in separate files** and always mounts the handler before body parsers and catch-all routes.
3. **Uses the server API on the server and the client API in the browser** — `auth.api.*` with `{ body, headers, query }` server-side, `authClient.*` client-side, never mixed.
4. **Adds both server and client plugins** for any feature called from the browser, and gives every client plugin a real `$InferServerPlugin`.
5. **Runs the CLI after schema changes** (`generate`, or `migrate` with the Kysely adapter) and notes when a plugin is a separate package.
6. **Fetches the live page** for precision-sensitive details (exact option lists, endpoint signatures) instead of guessing, and flags drift when the snapshot and the live docs differ.

The skill also points at Better Auth's own agent resources — the docs MCP server (`https://mcp.better-auth.com/mcp`), `llms.txt`, and the official skill pack (`npx skills add better-auth/skills`) — since the project publishes first-party guidance that may be fresher than this snapshot.

## Files

- `SKILL.md` — entry point: setup non-negotiables, minimal server/client/mount examples, the rules that prevent most bugs, the verified API surface, and live-doc links.
- `references/setup-and-config.md` — installation, every core option, dynamic `baseURL`, `trustedOrigins` patterns, `advanced` options, rate limiting, the CLI reference, TypeScript requirements, and runtime notes.
- `references/database.md` — adapters, core schema, custom names, `additionalFields`, ID generation, `databaseHooks`, secondary storage, migrations, schema validation, and joins.
- `references/sessions-and-cookies.md` — session lifecycle, cookie cache strategies, stateless mode, the session management API, cookie configuration, cross-subdomain and Safari/ITP setup, and security behaviors.
- `references/authentication.md` — email/password, email verification, password reset, social providers, account linking, user management, user deletion, and `validateUserInfo`.
- `references/server-api-and-hooks.md` — `auth.api.*` conventions, `APIError`, before/after hooks with the full context surface, type inference, and `customSession`.
- `references/client.md` — creating the client, methods, `useSession`, fetch options, error codes, SSR hydration, client plugins, and type inference.
- `references/plugins.md` — the plugin catalog with verified import paths, per-plugin usage for the major plugins, and server/client plugin authoring.
- `references/integrations.md` — handler mounting, CORS, and session middleware for ten frameworks plus Cloudflare Workers.

## Example prompts

```text
Set up Better Auth in this Hono app with email/password, GitHub OAuth, and
PostgreSQL via Drizzle. Include the auth config, the mount, and the CLI commands.
```

```text
Add two-factor authentication and an admin dashboard to my existing Better Auth
setup. I'm on Next.js App Router.
```

```text
My Better Auth session isn't persisting in Safari but works in Chrome. Diagnose it.
```

```text
I want to add a `role` field to the user and make sure users can't set it
themselves. Show the config and the client-side type inference.
```

```text
Write a Better Auth plugin that adds a custom endpoint and exposes it on the client.
```

## Install

```sh
./install.sh --target claude --skill better-auth /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

The guidance was authored for this repository and condenses the official Better Auth documentation ([better-auth.com/docs](https://www.better-auth.com/docs), docs source in [better-auth/better-auth](https://github.com/better-auth/better-auth) under `docs/content/docs`). No LICENSE file is bundled with this skill. Better Auth's own agent resources are published separately at [better-auth/skills](https://github.com/better-auth/skills).
