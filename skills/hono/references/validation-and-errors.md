# Hono Validation & Error Handling

Source: https://hono.dev/docs/guides/validation and https://hono.dev/docs/api/exception

## Built-in validator

```ts
import { validator } from 'hono/validator'

app.post(
  '/posts',
  validator('form', (value, c) => {
    const body = value['body']
    if (!body || typeof body !== 'string') {
      return c.text('Invalid!', 400) // short-circuit with an error Response
    }
    return { body } // return the (transformed) validated value
  }),
  (c) => {
    const { body } = c.req.valid('form')
    return c.json({ message: 'Created!' }, 201)
  }
)
```

- Targets: `'json' | 'form' | 'query' | 'header' | 'cookie' | 'param'`.
- Multiple validators can be chained (`validator('param', …), validator('query', …), validator('json', …)`); each value is read back with `c.req.valid(target)`.

**Gotchas:**

- For `json`/`form`, the request **must** carry a matching `Content-Type` header, or the callback receives `{}`. This bites most often in tests via `app.request()` — set `headers: new Headers({ 'Content-Type': 'application/json' })`.
- For `header` validation, keys are **lowercase**: `value['idempotency-key']`, never `value['Idempotency-Key']`.

## Zod / Standard Schema (recommended)

Prefer a third-party schema validator over hand-rolled checks.

```sh
npm i @hono/zod-validator zod        # or: @hono/standard-validator + zod/valibot/arktype
```

```ts
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'

const route = app.post(
  '/posts',
  zValidator('form', z.object({ title: z.string(), body: z.string() })),
  (c) => {
    const { title, body } = c.req.valid('form') // fully typed
    return c.json({ ok: true }, 201)
  }
)
export type AppType = typeof route
```

Standard Schema variant — one validator for Zod, Valibot, and ArkType:

```ts
import { sValidator } from '@hono/standard-validator'
import * as v from 'valibot'

app.post('/author', sValidator('json', v.object({ name: v.string(), age: v.number() })), (c) => {
  const { name, age } = c.req.valid('json')
  return c.json({ message: `${name} is ${age}` })
})
```

Query params arrive as strings — coerce with `z.coerce.number()` etc. when the schema expects numbers.

## HTTPException

```ts
import { HTTPException } from 'hono/http-exception'

// message variant (text response)
throw new HTTPException(401, { message: 'Unauthorized' })

// custom Response (other content types, headers)
throw new HTTPException(401, {
  res: new Response('Unauthorized', { headers: { Authenticate: 'error="invalid_token"' } }),
})

// attach arbitrary cause data
throw new HTTPException(401, { message, cause })
```

Handle centrally with `app.onError`:

```ts
app.onError((err, c) => {
  if (err instanceof HTTPException) {
    return err.getResponse() // built from the error's status/message/res
  }
  console.error(err)
  return c.text('Internal Server Error', 500)
})
```

Notes:

- `err.getResponse()` does **not** include headers previously set on the `Context`; copy them onto a new `Response` if needed.
- The status passed to the constructor always wins over the status of a custom `res` passed alongside it.

## Global 404 and error handlers

```ts
app.notFound((c) => c.text('Custom 404', 404))
app.onError((err, c) => c.text('Custom Error', 500))
```

- `notFound` only fires from the **top-level** app — a sub-app's `notFound` is never called.
- Route-level `onError` takes priority over the parent's.
- `c.error` holds the thrown error inside middleware (after `next()`).

## Error-response typing for RPC

`app.onError` response shapes are not inferred into `hc` types automatically; merge them with `ApplyGlobalResponse`:

```ts
import type { ApplyGlobalResponse } from 'hono/client'

type AppWithErrors = ApplyGlobalResponse<typeof app, { 500: { json: { error: string } } }>
const client = hc<AppWithErrors>('http://localhost')
```
