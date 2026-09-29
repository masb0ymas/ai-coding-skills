# Better Auth — Authentication Methods

Source: https://www.better-auth.com/docs/basic-usage, /docs/authentication/email-password, /docs/concepts/oauth, /docs/concepts/users-accounts

## Email & password

```ts
emailAndPassword: {
  enabled: true,                  // required — nothing works without it
  autoSignIn: true,               // default; false means user signs in manually
  disableSignUp: false,
  requireEmailVerification: false,
  minPasswordLength: 8,
  maxPasswordLength: 128,
  resetPasswordTokenExpiresIn: 3600,
  revokeSessionsOnPasswordReset: false,
  sendResetPassword: async ({ user, url, token }, request) => { /* ... */ },
  onPasswordReset: async ({ user }, request) => { /* ... */ },
  password: { hash: async (pw) => ..., verify: async ({ hash, password }) => ... },
}
```

Client methods: `signUp.email`, `signIn.email`, `signOut`.

```ts
const { data, error } = await authClient.signUp.email({
  email, password, name,
  image,                        // optional
  callbackURL: "/dashboard",    // after email verification
}, {
  onRequest: (ctx) => {},
  onSuccess: (ctx) => {},
  onError: (ctx) => alert(ctx.error.message),
});
```

```ts
await authClient.signIn.email({
  email, password,
  rememberMe: true,             // false → signed out when browser closes
  callbackURL: "/dashboard",
});
```

**Never call these from the server.** Server-side equivalent:

```ts
const response = await auth.api.signInEmail({
  body: { email, password },
  asResponse: true,             // returns a Response instead of data
});
```

Server calls that set cookies need the cookies forwarded to the client — Next.js and SvelteKit have plugins for this.

## Email verification

```ts
emailVerification: {
  sendVerificationEmail: async ({ user, url, token }, request) => {
    void sendEmail({ to: user.email, subject: "Verify your email", text: url });
  },
  sendOnSignUp: true,               // undefined → follows requireEmailVerification
  sendOnSignIn: false,
  autoSignInAfterVerification: true,
  expiresIn: 3600,
}
```

**Do not await the send** — use `void` (or `waitUntil` on serverless) to avoid timing attacks.

Require verification before login:

```ts
emailAndPassword: {
  enabled: true,
  requireEmailVerification: true,
  onExistingUserSignUp: async ({ user }, request) => { /* notify existing user */ },
}
```

Notes:
- Social sign-in is **not** gated by `emailAndPassword.requireEmailVerification`; each provider has its own opt-in `requireEmailVerification`.
- With `requireEmailVerification: true` (or `autoSignIn: false`), sign-up returns 200 for an already-registered email to prevent enumeration. Plugins that add user fields need `customSyntheticUser` so the fake response matches a real one.
- `/change-email` always returns success for the same reason.

Client: `authClient.sendVerificationEmail({ email, callbackURL })`.

## Password reset

```ts
emailAndPassword: {
  enabled: true,
  sendResetPassword: async ({ user, url, token }, request) => {
    void sendEmail({ to: user.email, subject: "Reset password", text: url });
  },
  revokeSessionsOnPasswordReset: true,
}
```

Client: `requestPasswordReset({ email, redirectTo })`, then `resetPassword({ newPassword, token })`.

## Social / OAuth providers

```ts
socialProviders: {
  github: {
    clientId: process.env.GITHUB_CLIENT_ID as string,
    clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
  },
  google: {
    clientId: process.env.GOOGLE_CLIENT_ID as string,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    accessType: "offline",       // request a refresh token
    prompt: "select_account",
  },
}
```

Callback URL pattern: `<baseURL>/api/auth/callback/<provider>`.

```ts
await authClient.signIn.social({
  provider: "github",
  callbackURL: "/dashboard",
  errorCallbackURL: "/error",
  newUserCallbackURL: "/welcome",
  disableRedirect: false,
});

// or authenticate with tokens you already hold (native SDK / mobile):
await authClient.signIn.social({ provider: "google", idToken: { token: "..." } });
```

Per-provider options worth knowing: `scope`, `redirectURI`, `mapProfileToUser`, `disableSignUp`, `disableImplicitSignUp`, `overrideUserInfoOnSignIn`, `requireEmailVerification` (opt-in, only for providers with a trustworthy `email_verified`), `getUserInfo`, `refreshAccessToken`, `verifyIdToken`, `disableIdTokenSignIn`.

## Accounts: linking & unlinking

An account = one auth method linked to a user. `providerId` + `accountId` identify the provider-side identity; the row `id` is what account APIs want.

```ts
account: {
  accountLinking: {
    enabled: true,                    // default
    trustedProviders: ["google", "github"],
    allowDifferentEmails: false,
    allowUnlinkingAll: false,
    disableImplicitLinking: false,    // true → same-email OAuth sign-in is rejected, not linked
    updateUserInfoOnLink: false,      // true → copy provider profile on link
  },
}
```

```ts
const { data: accounts, error } = await authClient.listAccounts();
const google = accounts?.find((a) => a.providerId === "google");

await authClient.linkSocial({ provider: "google", callbackURL: "/callback" });
await authClient.linkSocial({
  provider: "google",
  callbackURL: "/callback",
  scopes: ["https://www.googleapis.com/auth/drive.readonly"],  // incremental auth; merged into account.scope
});
await authClient.unlinkAccount({ accountId: google.id });      // row id, not providerId
```

Better Auth refuses to unlink a user's only account unless `allowUnlinkingAll: true`.

Linking credential accounts: a "forgot password" flow, or server-only `auth.api.setPassword({ body: { newPassword }, headers })`.

**Account selectors are `accountId`, never `providerId`** — `getAccessToken`, `refreshToken`, and `accountInfo` require the row id or `useAccountCookie: true`.

```ts
const { accessToken } = await authClient.getAccessToken({ accountId: account.id });
```

## User management

```ts
await authClient.updateUser({ name: "New Name", image: "..." });

// Change email (disabled by default)
user: {
  changeEmail: {
    enabled: true,
    sendChangeEmailConfirmation: async ({ user, newEmail, url, token }, request) => {
      void sendEmail({ to: user.email, ... });   // sent to the CURRENT email
    },
    updateEmailWithoutVerification: false,
  },
}
```

Without `updateEmailWithoutVerification`, the email changes only after verifying the **new** address. `sendChangeEmailConfirmation` adds a confirmation step on the current address first.

```ts
await authClient.changeEmail({ newEmail: "new@example.com", callbackURL: "/dashboard" });

await authClient.changePassword({
  newPassword, currentPassword, revokeOtherSessions: true,
});
```

Server-only password helpers: `auth.api.setPassword({ body: { newPassword }, headers })` and `auth.api.verifyPassword({ body: { password }, headers })`.

## Delete user

Disabled by default.

```ts
user: {
  deleteUser: {
    enabled: true,
    sendDeleteAccountVerification: async ({ user, url, token }, request) => { /* ... */ },
    beforeDelete: async (user, request) => { /* throw APIError to abort */ },
    afterDelete: async (user, request) => { /* cleanup */ },
  },
}
```

To delete, the user must satisfy one of: valid password (`deleteUser({ password })`), a fresh session, enabled email verification (needed for OAuth users), or a custom verification token (`deleteUser({ token })`). Freshness is controlled by `session.freshAge`; setting it to `0` disables that check.

## `validateUserInfo` — the identity policy gate

Fires before a user is created (`create-user`), before a provider account is linked (`link-account`), and on repeat OAuth/SSO sign-in (`sign-in`) — for every method, including stateless setups. Return nothing to allow; return `{ error, errorDescription }` to reject.

```ts
user: {
  validateUserInfo: ({ user, source }) => {
    if (!user.email?.endsWith("@example.com")) {
      return { error: "email_not_allowed", errorDescription: "Use your company email" };
    }
  },
}
```

`source.action` is `"create-user" | "link-account" | "sign-in"`; `source.method` is the auth method; `source.oauth`/`source.sso` carry the raw provider payload. Prefer this over per-provider checks for domain/org policy. `databaseHooks.user.create.before` still runs afterward for data shaping.

## Other sign-in methods (plugins)

Email OTP, magic link, passkey, username, phone number, anonymous, one-tap, SIWE, and generic OAuth are plugins — see the Plugins reference for correct import paths.
