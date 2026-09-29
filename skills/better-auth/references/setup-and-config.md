# Better Auth — Setup & Configuration

Source: https://www.better-auth.com/docs/installation, /docs/reference/options, /docs/concepts/cli, /docs/concepts/typescript

## Install & first instance

```sh
npm install better-auth
npx auth@latest secret          # or: openssl rand -base64 32
```

```txt title=".env"
BETTER_AUTH_SECRET=              # 32+ chars, high entropy
BETTER_AUTH_URL=http://localhost:3000
```

```ts title="auth.ts"
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  // database, providers, plugins...
});
```

Config file locations the CLI searches: `./auth.ts`, `./lib/auth.ts`, `./utils/auth.ts`, and any of those under `src/`, `app/`, `server/`. Export as `auth` or default.

## Core options

| Option | Default | Notes |
| --- | --- | --- |
| `appName` | `"Better Auth"` | Shown as TOTP issuer in authenticator apps; overridable per plugin |
| `baseURL` | `BETTER_AUTH_URL`, else inferred | Set explicitly. String or `{ allowedHosts, protocol, fallback }` for multi-domain |
| `basePath` | `/api/auth` | Overridden if `baseURL` contains a path |
| `secret` | `BETTER_AUTH_SECRET`, else `AUTH_SECRET` | Throws in production if unset |
| `trustedOrigins` | `[baseURL]` | Static array, async fn, or wildcard patterns |
| `database` | — | Adapter instance, driver, or omitted (stateless mode) |
| `secondaryStorage` | — | KV store for sessions/verification/rate limits |
| `rateLimit` | on in prod, off in dev | `{ enabled, window, max, storage, customRules }` |
| `advanced` | — | Cookies, IDs, cross-subdomain, CSRF, IP headers, `database.joins` |
| `logger` | — | `{ disabled, level, log }` |
| `telemetry` | enabled | `{ enabled: false }` to opt out |
| `disabledPaths` | — | Array of endpoint paths to disable |

### Dynamic `baseURL`

Use the object form for preview deployments or multiple hosts. `allowedHosts` supports exact, `*`/`**` wildcards, and port wildcards (`localhost:*`); entries are auto-added to `trustedOrigins`.

```ts
baseURL: {
  allowedHosts: ["myapp.com", "www.myapp.com", "*.vercel.app"],
  protocol: "https",
  fallback: "https://myapp.com",
}
```

Forwarded host/protocol headers are ignored unless `advanced.trustedProxyHeaders: true`.

### `trustedOrigins` patterns

| Pattern | Matches |
| --- | --- |
| `?` | Exactly one character (not `/`) |
| `*` | Zero or more characters, not crossing `/` |
| `**` | Zero or more characters including `/` |

`http://*.example.com` matches `http://api.example.com` and `http://api.app.example.com`. Custom schemes (`myapp://`, `exp://192.168.*.*:*/**`) match against the full URL including paths.

The async form receives the request, which is `undefined` during initialization and on `auth.api` calls — always handle that case.

## `advanced` highlights

```ts
advanced: {
  cookiePrefix: "my-app",                     // default "better-auth"
  useSecureCookies: true,                     // default: NODE_ENV === "production"
  crossSubDomainCookies: { enabled: true, domain: "app.example.com" },
  defaultCookieAttributes: { sameSite: "lax" },
  trustedProxyHeaders: false,
  disableCSRFCheck: false,                    // dangerous
  disableOriginCheck: false,                  // dangerous; also disables CSRF
  ipAddress: { ipAddressHeaders: ["x-forwarded-for"] },
  database: {
    generateId: false | "serial" | "uuid" | ((opts) => string | false),
    joins: true,                              // v1.4+; single-query joins
    validateSchema: false,
  },
}
```

`disableOriginCheck: true` disables URL validation **and** CSRF protection (backward compat). There is no option that disables only URL validation.

## Rate limiting

```ts
rateLimit: {
  enabled: true,
  window: 10,          // seconds
  max: 100,
  storage: "memory",   // "memory" | "database" | "secondary-storage"
  customRules: { "/sign-in/email": { window: 60, max: 5 } },
}
```

## CLI

| Command | Purpose |
| --- | --- |
| `npx auth@latest generate` | Emit schema for Prisma/Drizzle/Kysely. `--adapter`, `--dialect`, `--output`, `-y` |
| `npx auth@latest migrate` | Apply schema directly — **Kysely adapter only** |
| `npx auth@latest check schema` | Verify the schema can hold what Better Auth writes |
| `npx auth@latest create-admin` | Create an initial admin (requires the Admin plugin) |
| `npx auth@latest init` | Scaffold (Next.js + SQLite only) |
| `npx auth@latest upgrade` | Bump `better-auth` + official `@better-auth/*` packages |
| `npx auth@latest info` | Diagnostics; secrets auto-redacted. `--json` |
| `npx auth@latest secret` | Generate a secret |

`generate --adapter prisma --dialect postgresql` works without a live database connection. Kysely always introspects the configured database.

Postgres non-default schemas: set `database.schemaName`, otherwise `migrate` uses the connection `search_path`.

## TypeScript

Better Auth is built for `strict: true`. If you can't enable it, at minimum set `strictNullChecks: true` — and keep `declaration` and `composite` **off** to avoid "inference exceeds maximum length" errors.

```ts
export type Session = typeof auth.$Infer.Session;              // server
export type Session = typeof authClient.$Infer.Session;        // client
```

`$Infer.Session` has `{ session, user }`. Additional fields and plugin fields flow into it automatically.

## Runtime notes

- **CommonJS is not supported** — ESM only.
- **Cloudflare Workers** need `nodejs_compat` (or `nodejs_als`) in `wrangler.toml` for `AsyncLocalStorage`.
- **Express v5** changed wildcards: use `app.all("/api/auth/{*any}", toNodeHandler(auth))`.
- Mount the auth handler **before** body-parsing middleware and before any catch-all route.
