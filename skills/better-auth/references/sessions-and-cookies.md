# Better Auth — Sessions & Cookies

Source: https://www.better-auth.com/docs/concepts/session-management, /docs/concepts/cookies, /docs/reference/security

## Session model

Traditional cookie-based sessions. The opaque, secret-signed `session_token` cookie is the server-side session identifier; the server looks it up and returns the user. `session_data` exists only when `session.cookieCache` is enabled.

Session table fields: `id`, `token`, `userId`, `expiresAt`, `ipAddress`, `userAgent`, `createdAt`, `updatedAt`.

## Expiration, refresh, freshness

```ts
session: {
  expiresIn: 60 * 60 * 24 * 7,   // default 7 days
  updateAge: 60 * 60 * 24,       // default 1 day — extend expiry when used after this
  freshAge: 60 * 60 * 24,        // default 1 day; sensitive ops need a fresh session
  disableSessionRefresh: true,   // never extend, regardless of updateAge
  deferSessionRefresh: true,     // GET becomes read-only; returns needsRefresh, client POSTs
}
```

`freshAge: 0` disables the freshness check (not recommended if you rely on freshness for delete/password flows).

`deferSessionRefresh` exists for read-replica setups where GET must not write.

## Cookie cache

Avoids a DB roundtrip per `useSession`/`getSession` by storing signed session data in a short-lived cookie.

```ts
session: {
  cookieCache: {
    enabled: true,
    maxAge: 5 * 60,          // seconds
    strategy: "compact",     // "compact" | "jwt" | "jwe"
    refreshCache: true,      // refresh at 80% of maxAge (or { updateAge: 60 })
    version: "2",            // bump to invalidate every cached session
  },
}
```

| Strategy | Size | Security | Readable | Interoperable |
| --- | --- | --- | --- | --- |
| `compact` (default) | Smallest | Signed (HMAC-SHA256) | Yes | No |
| `jwt` | Medium | Signed (HS256) | Yes | Yes |
| `jwe` | Largest | Encrypted (A256CBC-HS512) | No | Yes |

**Revocation caveat:** with cookie cache on, a revoked session can stay usable on other devices until `maxAge` expires — the server cannot delete another device's cookie. If immediate revocation matters, disable the cache, shorten `maxAge`, or force a DB read with `disableCookieCache: true` on sensitive operations:

```ts
await auth.api.getSession({
  query: { disableCookieCache: true },
  headers: await headers(),
});
```

JWKS-backed cookie-cache JWTs (verify the `session_data` cookie against the JWT plugin's JWKS rather than the shared secret):

```ts
plugins: [jwt({ sessionCookieCache: true })],
session: { cookieCache: { enabled: true, strategy: "jwt" } }
```

This affects only `session_data`; `session_token` stays opaque, and cookie-cache JWTs are not interchangeable with the JWT plugin's `/token` output.

## Session management API

| Client | Server | Purpose |
| --- | --- | --- |
| `getSession()` | `auth.api.getSession({ headers })` | Current session |
| `useSession()` | — | Reactive hook (React/Vue/Svelte/Solid) |
| `listSessions()` | `auth.api.listSessions({ headers })` | All active sessions |
| `revokeSession({ token })` | `auth.api.revokeSession({ body: { token }, headers })` | End one session |
| `revokeOtherSessions()` | same | End all but current |
| `revokeSessions()` | same | End all |
| `updateSession({ ... })` | `auth.api.updateSession({ body, headers })` | Update **additional** session fields only |

Core fields (`token`, `userId`, `expiresAt`, `createdAt`, `updatedAt`, `ipAddress`, `userAgent`) cannot be updated through `updateSession`.

Revoke other sessions on password change: `authClient.changePassword({ newPassword, currentPassword, revokeOtherSessions: true })`.

## Stateless sessions (no database)

Omit `database` and Better Auth enables stateless mode automatically: the session lives in a signed/encrypted cookie and the server never queries a DB.

```ts
export const auth = betterAuth({
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 7 * 24 * 60 * 60,
      strategy: "jwe",
      refreshCache: true,
    },
  },
  account: {
    storeStateStrategy: "cookie",
    storeAccountCookie: true,
  },
});
```

`refreshCache` refreshes before expiry without a DB: `false` (no refresh), `true` (refresh at 80% of `maxAge`), or `{ updateAge: seconds }`.

Invalidate all stateless sessions by bumping `cookieCache.version` and redeploying.

Stateless + secondary storage combines cookie validation with Redis-backed revocation:

```ts
export const auth = betterAuth({
  secondaryStorage: { get, set, delete },
  session: { cookieCache: { maxAge: 5 * 60, refreshCache: false } },
});
```

Stateless account cookies hold OAuth token material; forward returned `Set-Cookie` headers when refreshing, and prefer DB-backed accounts for providers issuing large JWTs.

## Cookies

Default names follow `${prefix}.${cookie_name}` with prefix `better-auth`:

| Cookie | Purpose |
| --- | --- |
| `session_token` | Session identifier (always present) |
| `session_data` | Cached session data (only with `cookieCache`) |
| `dont_remember` | Set when `rememberMe` is disabled |

Plugins add their own (e.g. `two_factor`).

```ts
advanced: {
  cookiePrefix: "my-app",
  useSecureCookies: true,               // default: production only
  crossSubDomainCookies: { enabled: true, domain: "app.example.com" },
  cookies: {
    session_token: {
      name: "custom_session_token",
      attributes: { /* ... */ },
    },
  },
}
```

All cookies are `httpOnly`, `sameSite: "lax"`, and `secure` in production. Customizing cookie names reduces fingerprinting.

### Cross-subdomain sharing

Setting `domain` to a root domain exposes the cookie to every subdomain. Prefer the most specific scope (`app.example.com` over `.example.com`) and add the origins to `trustedOrigins`:

```ts
advanced: { crossSubDomainCookies: { enabled: true, domain: "app.example.com" } },
trustedOrigins: ["https://example.com", "https://app1.example.com"],
```

### Safari / ITP

Safari blocks third-party cookies, so a frontend on `app.domainB.com` calling `domainA.com` will lose sessions (works in Chrome, fails in Safari). Fix by either proxying the API through the frontend's own domain (Netlify redirects / Vercel rewrites) or putting both on a shared parent domain with `crossSubDomainCookies`.

## Security-relevant behavior

- **Password hashing:** `scrypt` by default; override with `emailAndPassword.password.{hash,verify}`.
- **CSRF:** non-simple requests preferred; `Origin` validated against `trustedOrigins`; `SameSite=Lax`; Fetch Metadata used to block first-login CSRF on sign-in/sign-up form posts. `Origin: null` from `Referrer-Policy: no-referrer` is accepted only when `Sec-Fetch-Site` confirms same-origin.
- **OAuth:** state + PKCE stored via `account.storeStateStrategy` (`"database"` default, `"cookie"` for stateless); state cookie is validated on callback and the verification record deleted after use.
- **Secret rotation:** `BETTER_AUTH_SECRETS` / the `secrets` option version encrypted data so you can roll keys without invalidating existing records. Legacy bare-hex data still decrypts with the original secret.
- **IP headers:** configure `advanced.ipAddress.ipAddressHeaders` when behind a proxy; forwarded headers are otherwise ignored unless `advanced.trustedProxyHeaders: true`.
