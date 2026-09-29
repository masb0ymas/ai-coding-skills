# Better Auth — Plugins

Source: https://www.better-auth.com/docs/plugins, /docs/concepts/plugins, and each plugin page

## Installing a plugin

Server plugin → `plugins` array of `betterAuth`. Client plugin → `plugins` array of `createAuthClient`. Most features need **both**. After adding a server plugin, re-run `npx auth@latest generate` (or `migrate`) to add its tables/columns.

```ts
// auth.ts
import { betterAuth } from "better-auth";
import { twoFactor } from "better-auth/plugins";

export const auth = betterAuth({
  appName: "My App",             // used as the TOTP issuer
  plugins: [twoFactor()],
});

// auth-client.ts
import { createAuthClient } from "better-auth/client";
import { twoFactorClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [twoFactorClient({ twoFactorPage: "/two-factor" })],
});
```

## Import paths — verified against v1.7.6

**Built into `better-auth/plugins`:**

| Plugin | Import |
| --- | --- |
| Two-factor | `twoFactor` |
| Admin | `admin` |
| Organization (+ `createAccessControl`, `role`) | `organization` |
| Email OTP | `emailOTP` |
| Magic link | `magicLink` |
| Username | `username` |
| Anonymous | `anonymous` |
| Phone number | `phoneNumber` |
| Multi-session | `multiSession` |
| JWT | `jwt` |
| Bearer | `bearer` |
| Captcha | `captcha` |
| Have I Been Pwned | `haveIBeenPwned` |
| Last login method | `lastLoginMethod` |
| One tap | `oneTap` |
| SIWE | `siwe` |
| Generic OAuth (+ `auth0`, `keycloak`, `okta`, `slack`, `line`, `hubspot`, `patreon`, `gumroad`, `yandex`, `microsoftEntraId`) | `genericOAuth` |
| Device authorization | `deviceAuthorization` |
| One-time token | `oneTimeToken` |
| OAuth proxy | `oAuthProxy` |
| Open API | `openAPI` |
| Custom session | `customSession` |
| Test utils | `testUtils` |

**Separate packages — install and import from the package root:**

| Plugin | Package | Client |
| --- | --- | --- |
| Passkey | `@better-auth/passkey` | `@better-auth/passkey/client` |
| API key | `@better-auth/api-key` | `@better-auth/api-key/client` |
| SSO (SAML/OIDC) | `@better-auth/sso` | `@better-auth/sso/client` |
| SCIM | `@better-auth/scim` | — |
| OAuth 2.1 provider | `@better-auth/oauth-provider` | `@better-auth/oauth-provider/client` |
| MCP provider | `@better-auth/mcp` | — |
| Agent auth | `@better-auth/agent-auth` | — |
| CIMD | `@better-auth/cimd` | — |
| i18n | `@better-auth/i18n` | — |
| Stripe | `@better-auth/stripe` | — |

All official packages share the `1.7.6` release train; `@better-auth/agent-auth` is independently versioned (0.6.x). `npx auth@latest upgrade` bumps the synchronized ones.

```ts
import { passkey } from "@better-auth/passkey";
import { apiKey } from "@better-auth/api-key";
import { sso } from "@better-auth/sso";
```

**Third-party payment plugins** (not `@better-auth/*`): `@polar-sh/better-auth`, `autumn-js`, `@creem_io/better-auth`, `@commet/node`, `@dub/better-auth`, Dodo Payments.

## Two-factor (`twoFactor`)

Adds `twoFactorEnabled`, `twoFactorSecret`, `twoFactorBackupCodes` to the user table.

```ts
await authClient.twoFactor.enable({ password, method: "totp" });  // → { totpURI, backupCodes }
await authClient.twoFactor.verifyTotp({ code: "123456", trustDevice: true });
await authClient.twoFactor.verifyOtp({ code: "123456" });
await authClient.twoFactor.disable({ password });
await authClient.twoFactor.generateBackupCodes({ password });
```

- Method is `"totp"` (default) or `"otp"`; `otp` needs `otpOptions.sendOTP` on the server.
- **The method is `verifyTotp`, not `verifyTOTP`** — some docs snippets use the wrong casing and will not typecheck.
- Enabling requires a password by default; OAuth/passkey/magic-link users need `allowPasswordless: true`.
- With `method: "totp"`, `twoFactorEnabled` stays false until a code is verified, unless `skipVerificationOnEnable: true`.

## Admin (`admin`)

Adds `role`, `banned`, `banReason`, `banExpires` to the user table. A user is an admin if their role is `admin` or their id is in `adminUserIds`.

```ts
import { admin, createAccessControl } from "better-auth/plugins";

const ac = createAccessControl({ project: ["create", "read", "update", "delete"] });
const adminRole = ac.newRole({ project: ["create", "read"] });

export const auth = betterAuth({
  plugins: [admin({ defaultRole: "user", adminRoles: ["admin"], ac, roles: { admin: adminRole } })],
});
```

```ts
await authClient.admin.createUser({ email, password, name, role: "user", data: { customField: "x" } });
await authClient.admin.listUsers({ query: { limit: 100 } });
await authClient.admin.setRole({ userId, role: "admin" });
await authClient.admin.banUser({ userId, banReason, banExpiresIn });
await authClient.admin.impersonateUser({ userId });
```

First admin: `npx auth@latest create-admin --email admin@example.com --name "Admin" --role admin`.

## Organization (`organization`)

Multi-tenancy: organizations, members, invitations, teams, roles, and access control. The largest plugin — 4 tables plus `activeOrganizationId` on the session.

```ts
import { organization } from "better-auth/plugins";

organization({
  allowUserToCreateOrganization: true,
  organizationLimit: 5,
  creatorRole: "owner",
  invitationExpiresIn: 60 * 60 * 48,
});
```

```ts
await authClient.organization.create({ name: "Org", slug: "org" });
await authClient.organization.setActive({ organizationId });
await authClient.organization.inviteMember({ email, role: "member" });
await authClient.organization.listMembers();
```

## JWT (`jwt`)

Exposes `/token`, `/jwks`, and `getJwtToken` for services that verify JWTs instead of reading session cookies.

```ts
jwt({
  jwt: { definePayload: ({ user }) => ({ id: user.id, email: user.email }) },
  sessionCookieCache: true,   // sign the session_data cookie with the JWKS keys
})
```

## API key (`@better-auth/api-key`)

```ts
import { apiKey } from "@better-auth/api-key";
// client: import { apiKeyClient } from "@better-auth/api-key/client";

await authClient.apiKey.create({ name: "CI", expiresIn: 60 * 60 * 24 * 30 });
await authClient.apiKey.list();
await authClient.apiKey.delete({ keyId });
```

## Bearer (`bearer`)

Lets API clients authenticate with `Authorization: Bearer <session-token>` instead of cookies.

```ts
import { bearer } from "better-auth/plugins";
export const auth = betterAuth({ plugins: [bearer()] });
```

## Username (`username`)

```ts
import { username } from "better-auth/plugins";
// client: usernameClient() from better-auth/client/plugins
```

There is **no `authClient.username` namespace**. Username methods live on `signIn`/`signUp`:

```ts
await authClient.signIn.username({ username: "abc", password: "pw" });
await authClient.signUp.email({ email, password, name, username: "abc" });
```

## Passkey (`@better-auth/passkey`)

WebAuthn. Client side is required for registration/authentication ceremonies.

```ts
import { passkey } from "@better-auth/passkey";
// client: import { passkeyClient } from "@better-auth/passkey/client";

passkey({ rpID: "example.com", rpName: "My App" });

await authClient.passkey.addPasskey({ name: "My laptop" });
await authClient.signIn.passkey();
await authClient.passkey.listUserPasskeys();
```

## Other commonly used plugins

- **`emailOTP`** — `authClient.emailOtp.sendVerificationOtp({ email, type: "sign-in" })`; needs `sendVerificationOTP` server-side.
- **`magicLink`** — `authClient.signIn.magicLink({ email })`; needs `sendMagicLink` server-side.
- **`multiSession`** — several concurrent sessions; `authClient.multiSession.listDeviceSessions()`, `setActive({ sessionToken })`.
- **`phoneNumber`** — needs `sendOTP`; adds `phoneNumber`/`phoneNumberVerified` to the user table.
- **`anonymous`** — guest sessions, later upgraded via `onLinkAccount`.
- **`genericOAuth`** — any OAuth provider via a `config` array; built-in helpers for Auth0, Keycloak, Okta, Slack, Line, HubSpot, Patreon, Gumroad, Yandex, Microsoft Entra ID.
- **`openAPI`** — generates an OpenAPI reference for your auth endpoints.
- **`testUtils`** — helpers for integration/E2E tests.
- **`@better-auth/sso`** — SAML 2.0 + OIDC enterprise SSO; `authClient.signIn.sso({ providerId, callbackURL })`.
- **`@better-auth/stripe`** — subscriptions; `stripe({ stripeClient, stripeWebhookSecret })`.

## Writing a custom server plugin

```ts
import type { BetterAuthPlugin } from "better-auth";
import { createAuthEndpoint } from "better-auth/api";

export const myPlugin = (options?: { /* ... */ }) => {
  return {
    id: "my-plugin",                 // required, unique
    endpoints: {
      // createAuthEndpoint(path, config, handler)
    },
    schema: { /* extra tables/columns */ },
    hooks: { before: [], after: [] },
    middleware: [],
    rateLimit: [],
    onRequest: async (request, ctx) => {},
    onResponse: async (response, ctx) => {},
  } satisfies BetterAuthPlugin;
};
```

A plugin can: add `endpoints`, extend `schema`, register `middleware` (route-matcher targeted), register `hooks` (specific route, and they also fire on direct `auth.api` calls), add `onRequest`/`onResponse`, and define `rateLimit` rules.

Register the plugin type so `getPlugin()` returns it exactly:

```ts
declare module "@better-auth/core" {
  interface BetterAuthPluginRegistry<AuthOptions, Options> {
    "my-plugin": { creator: typeof myPlugin };
  }
}
```

This is TypeScript-only — users still add the plugin to their `plugins` array.

## Writing a custom client plugin

```ts
import type { BetterAuthClientPlugin } from "better-auth/client";
import type { myPlugin } from "./plugin";

export const myPluginClient = {
  id: "my-plugin",
  $InferServerPlugin: {} as ReturnType<typeof myPlugin>,   // required for typed endpoints
  pathMethods: { "/my-plugin/hello-world": "POST" },        // override inferred GET/POST
  getActions: ($fetch) => ({
    myCustomAction: async (data: { foo: string }, fetchOptions?: BetterFetchOption) => {
      return $fetch("/custom/action", { method: "POST", body: { foo: data.foo }, ...fetchOptions });
    },
  }),
  getAtoms: ($fetch) => ({ myAtom: atom<null>() }),          // nanostores, for hooks
} satisfies BetterAuthClientPlugin;
```

Conventions: one argument plus optional `fetchOptions`, return `{ data, error }`. Endpoint paths convert kebab-case to camelCase on the client (`/my-plugin/hello-world` → `myPlugin.helloWorld`).

**Omit `$InferServerPlugin` and every other plugin's inferred types break** — not just this one's.
