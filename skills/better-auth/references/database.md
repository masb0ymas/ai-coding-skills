# Better Auth — Database

Source: https://www.better-auth.com/docs/concepts/database, /docs/adapters/*

## Adapters

```ts
// Built-in Kysely (driver directly)
import { Pool } from "pg";
export const auth = betterAuth({ database: new Pool() });
// also: better-sqlite3 `new Database("./sqlite.db")`, mysql2 `createPool()`

// Drizzle
import { drizzleAdapter } from "better-auth/adapters/drizzle";
export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "pg" }),   // "pg" | "mysql" | "sqlite"
});

// Prisma
import { prismaAdapter } from "better-auth/adapters/prisma";
export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),
});

// MongoDB
import { mongodbAdapter } from "better-auth/adapters/mongodb";
export const auth = betterAuth({ database: mongodbAdapter(client) });
```

With an ORM adapter, import `betterAuth` from `better-auth/minimal` to cut bundle size.

## Core schema

Four tables. Field names below are the Better Auth names; DB column names are configurable.

**`user`** — `id` (PK), `name`, `email` (unique), `emailVerified` (bool), `image?`, `createdAt`, `updatedAt`

**`session`** — `id` (PK), `userId` (FK→user, indexed, cascade delete), `token` (unique), `expiresAt`, `ipAddress?`, `userAgent?`, `createdAt`, `updatedAt`

**`account`** — `id` (PK), `userId` (FK), `accountId`, `providerId`, `accessToken?`, `refreshToken?`, `accessTokenExpiresAt?`, `refreshTokenExpiresAt?`, `scope?`, `idToken?`, `password?`, `createdAt`, `updatedAt`

**`verification`** — `id` (PK), `identifier` (indexed), `value`, `expiresAt`, `createdAt`, `updatedAt`

Account identity: `providerId` + `accountId` identify the **external** account; `id` is the **local** row. Account APIs want `id`. Credential (password) accounts use `providerId: "credential"` and the user's id as `accountId`.

## Custom table & column names

```ts
export const auth = betterAuth({
  user: {
    modelName: "users",
    fields: { name: "full_name", email: "email_address" },
  },
  session: {
    modelName: "user_sessions",
    fields: { userId: "user_id" },
  },
});
```

Type inference still uses the Better Auth names (`user.name`, not `user.full_name`).

Plugins take their own `schema` option:

```ts
twoFactor({ schema: { user: { fields: { twoFactorEnabled: "two_factor_enabled" } } } })
```

## Extending the schema — `additionalFields`

```ts
export const auth = betterAuth({
  user: {
    additionalFields: {
      role: {
        type: ["user", "admin"],   // string[] acts as an enum
        required: false,
        defaultValue: "user",
        input: false,              // server-owned: users cannot set it
      },
      lang: { type: "string", required: false, defaultValue: "en" },
    },
  },
});
```

- `input` (default `true`) — whether API input and provider profile mapping can supply the field.
- `returned` (default `true`) — whether the stored value is included in responses.
- `defaultValue` applies in the JS layer only; the DB column stays optional.

These are independent: `{ input: false, returned: true }` is valid (server-owned but visible). **Always set `input: false` on privilege fields like `role`** — otherwise users can self-assign.

Social providers can populate input-allowed fields via `mapProfileToUser`:

```ts
github: {
  clientId: "...", clientSecret: "...",
  mapProfileToUser: (profile) => ({
    firstName: profile.name.split(" ")[0],
    lastName: profile.name.split(" ")[1],
  }),
}
```

`mapProfileToUser` runs server-side but its return value is still treated as provider input — `input: false` fields are ignored.

Client-side inference: `inferAdditionalFields<typeof auth>()` in a monorepo, or the object form across separate projects.

## ID generation

```ts
advanced: {
  database: {
    generateId: false,                 // let the DB generate for all tables
    // generateId: "serial",           // auto-increment numeric (schema generated as numeric)
    // generateId: "uuid",             // UUID type where supported, else string
    // generateId: (opts) => opts.model === "user" ? false : crypto.randomUUID(),
  },
}
```

Returning `false`/`undefined` from the callback defers that model to the database. `"serial"` makes Better Auth infer `id` as string and convert on read/write — ids come back as strings of numbers, and every id you pass in must be a string.

Mixed ID types (e.g. serial users + UUID sessions) are supported with the callback form.

## `databaseHooks`

Lifecycle hooks for `user`, `session`, and `account`, each with `create`/`update`/`delete`, each with `before` and `after`.

```ts
export const auth = betterAuth({
  databaseHooks: {
    user: {
      create: {
        before: async (user, ctx) => {
          return { data: { ...user, firstName: user.name.split(" ")[0] } };
        },
        after: async (user) => { /* e.g. create a Stripe customer */ },
      },
      delete: {
        before: async (user) => {
          if (user.email.includes("admin")) return false;  // abort
          return true;
        },
      },
    },
  },
});
```

- `before` returning `false` aborts; returning `{ data }` replaces the payload. Return **Better Auth field names**, not DB column names.
- Throw `APIError` from `better-auth/api` to reject with a specific status.
- `ctx` (second arg) is **nullable** under `strict` — guard before reading `ctx.context.session`.
- `ctx.context.session` is `{ session, user }`, not a bare session row.
- Type inference for `additionalFields` inside hooks is incomplete — expect to widen types.

## Secondary storage

A KV store for sessions, verification records, and rate-limit counters. Interface:

```ts
interface SecondaryStorage {
  get: (key: string) => Promise<unknown>;
  getAndDelete: (key: string) => Promise<unknown>;
  increment: (key: string, ttl: number) => Promise<number>;
  set: (key: string, value: string, ttl?: number) => Promise<void>;
  delete: (key: string) => Promise<void>;
}
```

Official Redis implementation:

```sh
npm i @better-auth/redis-storage ioredis
```

```ts
import { Redis } from "ioredis";
import { redisStorage } from "@better-auth/redis-storage";
const redis = new Redis(process.env.REDIS_URL!);
export const auth = betterAuth({
  secondaryStorage: redisStorage({ client: redis, keyPrefix: "better-auth:" }),
});
```

When secondary storage is configured, sessions live there instead of the DB (see Sessions reference for `storeSessionInDatabase`/`preserveSessionInDatabase`), and verification records move there too unless `verification.storeInDatabase: true`.

## Migrations

- `npx auth@latest generate` — schema/migration file for your ORM.
- `npx auth@latest migrate` — applies directly, **Kysely only**.
- Programmatic (Cloudflare D1, serverless) — **Kysely only**:

```ts
import { getMigrations } from "better-auth/db/migration";
const { toBeCreated, toBeAdded, runMigrations } = await getMigrations(auth.options);
await runMigrations();
```

`getMigrations` does **not** work with Prisma or Drizzle — use the CLI plus your ORM there.

## Schema validation

At initialization Better Auth compares the schema against what it writes and reports missing tables/columns through the logger; requests then await the same check and fail on mismatch. Kysely reads live DB metadata; Drizzle checks the schema object; Prisma checks the generated client model (so Drizzle/Prisma checks cannot detect unapplied migrations). Disable with `advanced.database.validateSchema: false`, or check explicitly with `npx auth@latest check schema`.

## Joins

Since v1.4, `advanced.database.joins: true` lets 50+ endpoints run a single joined query instead of several roundtrips. Your ORM schema must declare the relationships — rerun `generate`/`migrate` after enabling.
