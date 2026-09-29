# Better Auth — Client

Source: https://www.better-auth.com/docs/concepts/client, /docs/basic-usage

## Creating the client

One framework entry point; all share the same API and hooks.

```ts
import { createAuthClient } from "better-auth/react";   // also: /client (vanilla), /vue, /svelte, /solid
export const authClient = createAuthClient({
  baseURL: "http://localhost:3000",   // omit if the client and auth server share a domain
  fetchOptions: { /* better-fetch options */ },
  sessionOptions: {
    refetchInterval: 0,               // seconds; 0 disables polling
    refetchOnWindowFocus: true,
    refetchWhenOffline: false,
  },
  disableDefaultFetchPlugins: false,  // true for React Native / Expo
  plugins: [ /* client plugins */ ],
});
```

Keep the client and server instances in **separate files** (`auth.ts` vs `auth-client.ts`).

Non-default `basePath` → pass the full URL including the path, or use `basePath` separately.

You can also destructure methods: `export const { signIn, signUp, useSession } = createAuthClient()`.

## Methods

`signUp.email`, `signIn.email` / `signIn.social` / `signIn.username` / `signIn.sso` / `signIn.magicLink`, `signOut`, `getSession`, `useSession`, `hydrateSession`, `listSessions`, `revokeSession`, `revokeOtherSessions`, `revokeSessions`, `updateSession`, `updateUser`, `changeEmail`, `changePassword`, `setPassword` *(server only)*, `requestPasswordReset`, `resetPassword`, `sendVerificationEmail`, `deleteUser`, `listAccounts`, `linkSocial`, `unlinkAccount`, `getAccessToken`, plus one namespace per installed plugin (`admin`, `organization`, `twoFactor`, `passkey`, `apiKey`, `multiSession`, …).

## Session on the client

```tsx
const { data: session, isPending, error, refetch } = authClient.useSession();
```

`useSession` is a nanostores-backed hook; framework bindings: React (`{ data, isPending, error, refetch }`), Vue (`session.data`), Svelte (`$session.data`), Solid (call it: `session()`). Vanilla: `authClient.useSession.subscribe((value) => ...)`.

Non-reactive alternative: `const { data: session, error } = await authClient.getSession()`.

## Fetch options and callbacks

Options go either as the second argument or inside `fetchOptions`:

```ts
await authClient.signIn.email(
  { email, password },
  { onRequest: (ctx) => {}, onSuccess: (ctx) => {}, onError: (ctx) => {} },
);

await authClient.signIn.email({
  email, password,
  fetchOptions: { onError: (ctx) => {} },
});
```

`disableSignal: true` prevents an endpoint call from re-rendering hooks like `useSession` (useful for updates that don't change the session); call `refetch()` manually if needed.

## Errors

Every call returns `{ data, error }` — it does not throw.

```ts
const { data, error } = await authClient.signIn.email({ email, password });
if (error) {
  console.log(error.message, error.status, error.statusText, error.code);
}
```

`authClient.$ERROR_CODES` enumerates server error codes for building translations:

```ts
type ErrorTypes = Partial<Record<keyof typeof authClient.$ERROR_CODES, { en: string; es: string }>>;
```

## SSR hydration

`useSession` fetches on the client and flashes a loading state. Pass the server-fetched session to `hydrateSession` so the first render already has data:

```tsx
// client component
type Props = { initialSession: typeof authClient.$Infer.Session | null };

export function SessionCard({ initialSession }: Props) {
  authClient.hydrateSession(initialSession);
  const { data, isPending, isRefetching } = authClient.useSession();
  const session = isPending && !isRefetching ? initialSession : data;
  if (!session) return <p>Not signed in</p>;
  return <pre>{JSON.stringify(session, null, 2)}</pre>;
}
```

Only the first non-null `hydrateSession` call takes effect; `null` is ignored and `useSession` fetches normally.

## Client plugins

Required for any plugin whose endpoints you call from the browser — the server plugin alone does not add client methods.

```ts
import { createAuthClient } from "better-auth/client";
import { twoFactorClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [twoFactorClient({ twoFactorPage: "/two-factor" })],
});
```

Available from `better-auth/client/plugins`: `adminClient`, `organizationClient`, `twoFactorClient`, `multiSessionClient`, `emailOTPClient`, `magicLinkClient`, `usernameClient`, `anonymousClient`, `phoneNumberClient`, `jwtClient`, `oneTapClient`, `lastLoginMethodClient`, `siweClient`, `oneTimeTokenClient`, `deviceAuthorizationClient`, `customSessionClient`, `inferAdditionalFields`.

Plugins shipped as separate packages export their client from a `/client` subpath: `@better-auth/passkey/client`, `@better-auth/api-key/client`, `@better-auth/sso/client`, `@better-auth/oauth-provider/client`.

**Every client plugin must carry a real `$InferServerPlugin`.** A plugin object without it collapses the inferred types of *all sibling plugins* — `authClient.admin.listUsers` disappears even though `adminClient()` is installed.

## Inferring types

```ts
export type Session = typeof authClient.$Infer.Session;   // { session, user }
```

Additional fields across separate projects:

```ts
import { inferAdditionalFields } from "better-auth/client/plugins";

createAuthClient({
  plugins: [
    inferAdditionalFields<typeof auth>(),                     // monorepo: import server type
    inferAdditionalFields({ user: { role: { type: "string" } } }), // separate projects
  ],
});
```
