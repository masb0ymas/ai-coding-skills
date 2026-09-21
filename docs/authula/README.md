# Authula

Authula is an open-source, plugin-based authentication framework for Go ([github.com/Authula/authula](https://github.com/Authula/authula), docs at [authula.dev/docs](https://authula.dev/docs)). It solves the problem of wiring authentication into a Go backend by shipping every auth concern as a plugin that exposes named capabilities, so route protection is declared explicitly through route mappings rather than implied by enabling a plugin. Internally it uses Chi (routing), Bun ORM (database), and Watermill (event bus). This skill is a condensed snapshot of the Authula docs and guides the agent through configuring, embedding, and extending Authula. The bundled guidance was written for this repository.

## When to use it

- The user mentions Authula, authula.dev, `session.auth`, or "Authula config".
- The user wants to add or configure auth in a Go backend using Authula plugins: email-password, oauth2, session, jwt, totp, magic-link, csrf, rate-limit, organizations, access-control, admin, api-key, bearer, or secondary-storage.
- The user is working with `config.toml` route mappings, hooks, service hooks, custom routes, or writing a custom Authula plugin.
- The user wants to run Authula as a standalone auth server (Docker, `config.toml`) or embed it as a Go library.
- Code imports `github.com/Authula/authula` or any of its plugin subpackages.
- Not for: other Go auth libraries. The skill also does not attempt to guess plugin config keys, endpoints, or capability names that are missing from its references — for those, the live docs page must be fetched.

## What it covers

### Two operating modes

- **Library mode** — embed Authula in a Go app with `go get github.com/Authula/authula`; `auth.Handler()` returns a standard `http.Handler`.
- **Standalone mode** — run Authula as a server via the Docker image `ghcr.io/authula/authula:latest`, configured with `config.toml`. Usable from any stack; a Node.js SDK exists.

### Core mental model

1. Enable a plugin: `[plugins.<id>] enabled = true` in `config.toml`, or pass `<plugin>.New(...)` in `AuthConfig.Plugins` in library mode.
2. Protect routes with route mappings. An enabled plugin protects nothing by itself; routes are protected only when a mapping attaches a capability such as `session.auth` (401 without a valid session) or `session.auth.optional` (continue anonymously).
3. Route paths in mappings are relative to `base_path`. `GET:/me` with base path `/api/auth` is served at `/api/auth/me`.
4. Secrets belong in env vars, not `config.toml`: `AUTHULA_SECRET` (generate with `openssl rand -hex 32`), `AUTHULA_DATABASE_URL`, and OAuth client secrets.
5. Migrations run automatically when the Authula instance is created (core and plugin tables).

### Plugin index

| Plugin | Page | What it is |
| --- | --- | --- |
| Session | `session` | Cookie sessions with sliding renewal; capabilities `session.auth`, `session.auth.optional` |
| Email & Password | `email-password` | Sign-up, sign-in, verification, reset, email change |
| Email | `email` | Transactional email with multiple providers and automatic failover (SMTP in examples) |
| OAuth2 | `oauth2` (+ `oauth2/discord`, `oauth2/github`, `oauth2/google`) | Social login |
| TOTP | `totp` | Authenticator-app 2FA, backup codes, trusted devices |
| Magic Link | `magic-link` | Passwordless email links |
| JWT | `jwt` | JWT auth (Ed25519; key rotation per the security page) |
| Bearer | `bearer` | Bearer-token auth |
| API Key | `api-key` | API key auth |
| CSRF | `csrf` | Double-submit-cookie CSRF protection; capability `csrf.protect` |
| Rate Limit | `ratelimit` | Rate limiting (URL has no hyphen; config ID is `ratelimit`) |
| Secondary Storage | `secondary-storage` | In-memory, DB, or Redis key-value store for rate-limit counters and other high-frequency data |
| Access Control | `access-control` | Roles and permissions; used with route mapping `permissions` |
| Admin | `admin` | Admin endpoints |
| Organizations | `organizations` | Multi-tenant orgs |

Plugin pages under `https://www.authula.dev/docs/plugins/` share one layout: Overview, Configuration (standalone TOML and library Go), API Reference, Database Schema, Plugin Capabilities, Security Recommendations, and Client Plugin (TypeScript SDK). Plugins not captured in the skill's references must be fetched from their live page before config keys, endpoints, or capability names are given.

Session internals:

- Capabilities `session.auth` (401 when the cookie is missing or invalid) and `session.auth.optional` (continue anonymously). In Go: `sessionplugin.HookIDSessionAuth.String()` and `sessionplugin.HookIDSessionAuthOptional.String()`.
- Global hooks issue the session cookie after successful authentication and remove it on sign-out.
- No HTTP endpoints and no database tables of its own; works alongside other auth plugins such as JWT.
- Lifetime, cookie name, `secure`, `same_site`, `max_sessions_per_user`, and cleanup live in the global `[session]` table. Docs examples disagree on `expires_in` (24h vs 30m), so it should always be set explicitly. Tokens are hashed before storage.

Email & Password:

- Config keys under `[plugins.email_password]`: `enabled`, `min_password_length` (8 recommended), `max_password_length` (128), `disable_sign_up`, `require_email_verification`, `auto_sign_in`, `send_email_on_sign_up`, `send_email_on_sign_in`, `email_verification_expires_in` (24h), `password_reset_expires_in` (1h), `request_email_change_expires_in` (1h).
- The Email plugin ([plugins.email] enabled = true, provider = "smtp", from_address = "...") is needed for verification, reset, and change emails; SMTP credentials come from env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`).
- Library-only optional callbacks override sending: `SendEmailVerification`, `SendPasswordResetEmail`, `SendChangedPasswordEmail`, `SendRequestEmailChangeEmail`, `SendChangedEmailToOldEmail`, `SendChangedEmailToNewEmail`.
- No tables and no capabilities of its own. Passwords are hashed with Argon2.
- Endpoints (under the base path):

  | Method | Path |
  | --- | --- |
  | POST | `/email-password/sign-up` |
  | POST | `/email-password/sign-in` |
  | GET | `/email-password/verify-email` |
  | POST | `/email-password/send-email-verification` |
  | POST | `/email-password/request-password-reset` |
  | POST | `/email-password/change-password` |
  | POST | `/email-password/request-email-change` |

OAuth2 providers: Discord, GitHub, Google.

```toml
[plugins.oauth2]
enabled = true

[plugins.oauth2.providers.google]
enabled = true
client_id = "your-client-id"
client_secret = "..."          # prefer env vars (GOOGLE_CLIENT_SECRET etc.)
redirect_url = "http://localhost:8080/auth/oauth2/callback/google"
scopes = []
```

Endpoints: `GET /oauth2/authorize/{provider}` starts the flow; `GET /oauth2/callback/{provider}` handles the callback. The redirect URL includes the configured base path and must match what is registered with the provider. No tables, no capabilities.

TOTP:

```toml
[plugins.totp]
enabled = true
skip_verification_on_enable = false   # keep false: require password when enabling
backup_code_count = 10
trusted_device_duration = "720h"
trusted_devices_auto_cleanup = true
trusted_devices_cleanup_interval = "1h"
pending_token_expiry = "5m"
secure_cookie = true
same_site = "lax"
```

- Requires `app_name` to be set (used in the `otpauth://` URI).
- Endpoints:

  | Method | Path | Auth |
  | --- | --- | --- |
  | POST | `/totp/enable` | session; returns `totp_uri` and `backup_codes` |
  | POST | `/totp/disable` | session |
  | GET | `/totp/get-uri` | session |
  | POST | `/totp/generate-backup-codes` | session |
  | POST | `/totp/verify` | pending-token cookie; body `{code, trust_device?}` |
  | POST | `/totp/verify-backup-code` | pending-token cookie; single-use codes |

- Capability `totp.intercept`: during sign-in it sets a pending-token cookie and returns a response telling the client to redirect to the TOTP verification step.
- Tables: `totp` (encrypted secret, hashed backup codes) and `trusted_devices`. Events: `totp.enabled`, `totp.disabled`, `totp.verified`, `totp.backup_code_used`, `totp.device_trusted`.

### Setup and configuration (standalone)

Top-level `config.toml` keys and sections include `app_name`, `base_url`, `base_path`, `disabled_paths` (must be top-level, before any `[table]`), and the `[database]`, `[logger]`, `[session]`, `[verification]`, `[security]`, `[security.cors]`, and `[event_bus]` tables. Database providers: `sqlite | postgres | mysql`. Logger levels: `debug | info | warn | error`.

```bash
docker run -itd \
  -p 8080:8080 \
  -v ./config.toml:/home/appuser/config.toml \
  --env-file ./.env \
  ghcr.io/authula/authula:latest
```

Environment variables include `AUTHULA_CONFIG_PATH` (defaults to `./config.toml`), `AUTHULA_BASE_URL`, `AUTHULA_SECRET`, `AUTHULA_DATABASE_URL`, `GO_ENV`, `PORT`, the OAuth client ID/secret pairs, and `POSTGRES_URL` / `REDIS_URL` / `KAFKA_BROKERS` / `NATS_URL` / `RABBITMQ_URL` / `EVENT_BUS_CONSUMER_GROUP`.

Event bus providers: `gochannel` (in-memory, events lost on restart; fine for dev), `sqlite`, `postgres`, `redis`, `kafka`, `nats`, `rabbitmq` (the latter group enables distributed handling across instances). For sqlite, the file path is set in `[event_bus.sqlite] db_path`.

### Setup and configuration (library)

```go
import (
    authula "github.com/Authula/authula"
    authulaconfig "github.com/Authula/authula/config"
    authulamodels "github.com/Authula/authula/models"
)

config := authulaconfig.NewConfig(
    // Same options as config.toml, as functional options. Known ones include:
    // WithAppName, WithBasePath, WithDatabase, WithLogger, WithSession,
    // WithVerification, WithSecurity, WithEventBus, WithRouteMappings,
    // WithCoreServiceHooks. Full list: config/options.go in the repo.
)
auth := authula.New(&authula.AuthConfig{
    Config:  config,
    Plugins: []authulamodels.Plugin{ /* plugin instances */ },
})
```

Database: `authulaconfig.WithDatabase(authulamodels.DatabaseConfig{Provider: "sqlite", URL: "auth.db"})`. Mount with `http.ListenAndServe(":8080", auth.Handler())` or under a prefix with `http.Handle("/api/auth/", auth.Handler())`. The `Auth` type also exposes `RunCoreMigrations`, `DropCoreMigrations`, `Migrator()`, and `MigrationManager()`.

Library import pattern for plugins:

```go
import (
    sessionplugin "github.com/Authula/authula/plugins/session"
    emailpasswordplugin "github.com/Authula/authula/plugins/email-password"
    emailpasswordplugintypes "github.com/Authula/authula/plugins/email-password/types"
    oauth2plugin "github.com/Authula/authula/plugins/oauth2"
    oauth2plugintypes "github.com/Authula/authula/plugins/oauth2/types"
    totpplugin "github.com/Authula/authula/plugins/totp"
    totpplugintypes "github.com/Authula/authula/plugins/totp/types"
)
```

### Route mappings

Route mappings declare which plugin capabilities (and optionally permissions) run for which routes. Standalone uses repeated `[[route_mappings]]` tables; library mode uses `authulaconfig.WithRouteMappings([]authulamodels.RouteMapping{...})`.

- Fields: `paths` (one or more patterns), `plugins` (capabilities such as `session.auth`, `session.auth.optional`, `csrf.protect`), `permissions` (optional names enforced by the Access Control plugin).
- Path forms: `METHOD:/path` for a specific method; `/path` for all methods; `{param}` for dynamic segments (e.g. `GET:/access-control/roles/{role_id}`); `/prefix/*` for a subtree (e.g. `/organizations/*`).
- Several mappings can target the same route; Authula merges their plugin and permission lists, so session and permissions can be separated across mappings.
- Paths are base-path aware.
- A route with no mapping is still processed by Authula, just without extra capabilities.

```toml
[[route_mappings]]
paths = ["GET:/access-control/users/{user_id}/roles",
         "DELETE:/access-control/users/{user_id}/roles/{role_id}"]
plugins = ["session.auth"]

[[route_mappings]]
paths = ["/organizations/*"]
plugins = ["session.auth"]
```

### Disabled paths

`disabled_paths` makes Authula skip route registration entirely — used to hide plugin endpoints, exclude externally managed paths, or turn off groups during testing. It accepts the same three forms (`METHOD:/path`, `/path`, `/path/*`), matching is base-path aware, and it must be top-level, never inside `[plugins]` or another table.

```toml
# top-level only, not inside [plugins] or any other table
disabled_paths = [
  "GET:/email-password/request-email-change",
  "/organizations",
  "/admin/*",
]
```

Distinction: a route that stays available but needs auth or permissions gets a route mapping; a route Authula should not handle at all gets a disabled path.

### Security model

| Area | What Authula does |
| --- | --- |
| Password hashing | Argon2id (64 MB memory, 4 threads, 16-byte salts) |
| JWT signatures | Ed25519 |
| Data encryption | ChaCha20-Poly1305-X |
| Sessions | Sliding window with periodic revalidation; fingerprints IP and user agent; session tokens hashed in the database |
| JWT | Access/refresh pair; access token ~15 min, refresh ~7 days; automatic key rotation ~every 30 days with a 1-hour grace period |
| CSRF | Double-submit cookie (24-byte tokens via header) plus Go 1.25 `CrossOriginProtection` (`Sec-Fetch-Site`/`Origin`) |
| Rate limiting | In-memory, Redis, or DB backends with failover; `X-RateLimit` headers; proxy-aware client IP |
| Token invalidation | Redis-backed blacklist with TTL; `TokenReuseRecoveredEvent` (first reuse) and `TokenReuseMaliciousEvent` (repeated) |
| IP handling | Zero-trust: ignores `X-Forwarded-For` unless the source is in `trusted_proxies` |
| Headers and CORS | Strict origin validation, no wildcard with credentials; injects `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` |
| Config vaulting | Sensitive config keys are detected and encrypted in memory |

Security values come from the Security concepts page; where they conflict with defaults in `config.toml` or a plugin page, the config or plugin page wins for actual behaviour.

### Event bus

Auth events flow through a Watermill-based event bus. Plugins emit events (for example TOTP emits `totp.enabled`, `totp.disabled`, `totp.verified`, `totp.backup_code_used`, `totp.device_trusted`) that application code can subscribe to. In library mode, obtain the bus with `auth.EventBus()`.

### Router adapters

`auth.Handler()` is a plain `http.Handler`, so most routers need no adapter; only Fiber has an official adapter.

```go
// net/http
http.Handle("/api/auth/", auth.Handler())

// Chi (Authula already uses Chi internally)
r := chi.NewRouter()
r.Handle("/auth/*", auth.Handler())     // use your base path

// Echo
e := echo.New()
e.Any("/api/auth/*", echo.WrapHandler(auth.Handler()))

// Fiber v3 (official adapter)
import fiberadapter "github.com/Authula/authula/adapters/fiber"
app.Use("/api/auth", fiberadapter.New(fiberadapter.Config{Handler: auth.Handler()}))
```

Routes defined on your own router outside the Authula handler do not run Authula hooks; register them via `auth.RegisterCustomRoute(...)` to get hooks.

### Custom routes and `RequestContext`

```go
auth.RegisterCustomRoute(authulamodels.Route{
    Method: "GET",
    Path:   "/api/health",               // NOT prefixed with base_path
    Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        reqCtx, _ := authulamodels.GetRequestContext(r.Context())
        reqCtx.SetJSONResponse(http.StatusOK, map[string]any{"status": "ok"})
    }),
    // Middleware: []func(http.Handler) http.Handler{},
    // Metadata: map[string]any{"plugins": []string{"session.auth"}},
})
```

- `RegisterRoute` / `RegisterRoutes`: registered with the base path prefix.
- `RegisterCustomRoute` / `RegisterCustomRoutes`: without the prefix (application routes).
- `RegisterCustomRouteGroup(group)`: shared prefix and metadata for a group.
- `RegisterMiddleware(...)`: call before `Handler()`.
- `RegisterHook` / `RegisterHooks`.
- The `Route` struct: `Method`, `Path`, `Handler http.Handler`, `Middleware`, `Metadata map[string]any`. `Metadata["plugins"]` lists capabilities for the route (e.g. `"csrf.protect"`, `"session.auth"`).
- Custom routes are unauthenticated by default; add auth through `Metadata["plugins"]` or middleware.

`RequestContext` (from `authulamodels.GetRequestContext(r.Context())`) carries `Request`, `ResponseWriter`, `Path`, `Method`, `Headers`, `Actor`, `ClientIP`, `Values`, `Route`, and `Handled`. Helpers: `SetJSONResponse(status, payload)`, `SetResponse(status, headers, body)`, `SetActorInContext(actor)`. Setting `Handled = true` short-circuits remaining hooks in the stage. Read the authenticated actor in your own handlers with `auth.GetActorFromRequest(req)` or `auth.GetActorFromContext(ctx)`.

### Request hooks

Four stages:

| Stage | Runs | Typical use |
| --- | --- | --- |
| `HookOnRequest` | Very start of every request, before route matching | global logging, metrics |
| `HookBefore` | After route matching, before the handler | auth, authorization, validation |
| `HookAfter` | After the handler, before the response is sent | modify response, headers |
| `HookOnResponse` | After the response was written | analytics, audit (cannot change the response) |

```go
type Hook struct {
    Stage    HookStage
    PluginID string       // optional: only run if the route's metadata lists this plugin
    Matcher  HookMatcher  // optional: func(*RequestContext) bool
    Handler  HookHandler  // func(*RequestContext) error
    Order    int          // lower runs first; local to each PluginID group
    Async    bool         // background goroutine; side effects only
}
```

Rules: hooks without `PluginID` run for all routes; a handler error is logged and, in the default mode, the next hook still runs; error modes via `RouterOptions.HookErrorMode` are `error-log-continue` (default), `error-log-fail-fast`, and `error-silent`; `RouterOptions.AsyncHookTimeout` defaults to 30 s; share data across hooks with `reqCtx.Values` (avoid sensitive data). To block a request: `reqCtx.SetJSONResponse(401, ...)`, then `reqCtx.Handled = true`, then `return nil`.

```go
auth.RegisterHook(models.Hook{
    Stage: models.HookBefore,
    Matcher: func(rc *models.RequestContext) bool { return strings.HasPrefix(rc.Path, "/admin") },
    Handler: func(rc *models.RequestContext) error {
        if rc.Actor == nil || rc.Actor.Type != models.ActorUser {
            rc.SetJSONResponse(http.StatusUnauthorized, map[string]any{"message": "Authentication required"})
            rc.Handled = true
        }
        return nil
    },
})
```

Many common needs (session, JWT, CSRF, rate limit, RBAC) already exist as plugins, so a plugin should be checked before writing a hook.

### Service hooks

Run custom logic around core entity operations. Signature: `type ServiceHook[T any] func(*T) error`. Entities: Users, Accounts, Sessions (before/after create and update), and Verifications (before/after create only). Before hooks may mutate the entity before it is stored; after hooks are for side effects; returning an error aborts the operation.

```go
config := authulaconfig.NewConfig(
    authulaconfig.WithCoreServiceHooks(authulamodels.CoreServiceHooksConfig{
        Users: &authulamodels.ServiceHooks[authulamodels.User]{},
    }),
)
config.CoreServiceHooks.Users.RegisterAfterCreate(func(u *authulamodels.User) error {
    log.Printf("new user %s <%s>", u.ID, u.Email)
    return nil
})
```

### Programmatic API

Keep the `Auth` handle to call core operations without an HTTP round trip:

```go
me, err := auth.Api.GetMe(ctx, "user-id")
res, err := auth.Api.SignOut(ctx, "user-id", nil /*sessionID*/, false /*signOutAll*/)
```

Plugins expose their own `Api` field, reachable either by keeping the plugin instance or by looking it up from the registry:

```go
// 1) keep the plugin instance you created
ep := emailpasswordplugin.New(cfg)
auth := authula.New(&authula.AuthConfig{Config: c, Plugins: []authulamodels.Plugin{ep}})
result, err := ep.Api.SignIn(ctx, email, password, nil, nil, nil) // callbackURL, ip, userAgent

// 2) look it up from the registry after init
p, ok := auth.PluginRegistry.GetPlugin(authulamodels.PluginOrganizations.String()).(*organizations.OrganizationsPlugin)
```

Use `auth.Api` for core functionality, a plugin's `Api` for plugin features, and lower-level helpers only for custom routing. The `Auth` type also offers `CoreServices()`, `DB()` (Bun), `EventBus()`, and `Router()`.

### Custom plugins

Required interface:

```go
type Plugin interface {
    Metadata() PluginMetadata   // ID, Version, Description
    Config() any                // typed config struct
    Init(ctx *PluginContext) error
    Close() error
}

type PluginContext struct {
    DB              bun.IDB
    Logger          Logger
    EventBus        EventBus
    ServiceRegistry ServiceRegistry   // Register(name, svc) / Get(name)
    GetConfig       func() *Config
}
```

Plugins talk to each other through the service registry, for example `ctx.ServiceRegistry.Get(models.ServiceUser.String()).(services.UserService)`.

Optional capabilities (implement the interface to opt in):

| Interface | Method(s) | Adds |
| --- | --- | --- |
| `PluginWithMigrations` | `Migrations(provider string) []migrations.Migration`, `DependsOn() []string` | DB tables, per provider (sqlite/postgres/mysql) via `migrations.ForProvider` |
| `PluginWithRoutes` | `Routes() []Route` | HTTP endpoints |
| `PluginWithMiddleware` | `Middleware() []func(http.Handler) http.Handler` | global middleware |
| `AuthMethodProvider` | `AuthMiddleware()`, `OptionalAuthMiddleware()` | a new auth method (reject vs allow anonymous) |
| `PluginWithHooks` | `Hooks() []Hook` | lifecycle hooks |

Plugin IDs are lowercase with underscores. Config is a `[plugins.<id>]` TOML table; `util.LoadPluginConfig(ctx.GetConfig(), p.Metadata().ID, &p.config)` merges values in `Init`. Best practices: validate config in `Init`, release resources in `Close`, use the injected logger, use `Async: true` only for side effects, set the authenticated identity with `reqCtx.SetActorInContext(actor)`, keep responses consistent, and check whether an existing plugin or plain hook already covers the need.

### Pitfalls

- CORS + sessions: with the session plugin and `allow_credentials = true`, `allowed_origins` must list exact origins; `["*"]` is rejected by browsers.
- CSRF: the token header must also be listed in `security.cors.allowed_headers`.
- TOTP: keep `/totp/verify` and `/totp/verify-backup-code` reachable without `session.auth` (they rely on a pending-token cookie); set `app_name`.
- `disabled_paths` must be top-level.
- Trusted proxies: Authula ignores `X-Forwarded-For` unless the proxy CIDR is configured in `security.trusted_proxies`; behind a load balancer, rate limiting sees the wrong IP without it.
- Async hooks are for side effects only — never for auth, CSRF, or rate limiting.
- Docs contain small inconsistencies (e.g. `authulaconfig.New` vs `NewConfig`, or `authula.New(config)` vs `authula.New(&AuthConfig{...})`). The verified forms are `authulaconfig.NewConfig(...)` and `authula.New(&authula.AuthConfig{...})`; on compile errors, check the current pkg.go.dev page.
- Sample configs use `secure = false` for local development; set `secure = true` behind HTTPS in production.

## How it works

The skill is a task-routed reference set rather than a linear workflow. The agent:

1. **Establishes the situation before writing code** (asking only what it cannot infer): mode (library vs standalone), auth methods needed, database (SQLite, PostgreSQL, or MySQL), and — in library mode — the router (net/http, Chi, Echo, Fiber).
2. **Reads only the reference file that matches the task**, per the routing table in `SKILL.md`: setup/install/Docker/curl → `setup.md`; route protection, mappings, disabled paths, security → `routing-and-security.md`; adapters, custom routes, hooks, service hooks, programmatic API → `extending.md`; writing a plugin → `custom-plugins.md`; plugin config/endpoints and live doc URLs → `plugins.md`.
3. **Answers in the user's mode**: TOML for standalone, Go options for library — one of the two, not both.
4. **Shows the complete wiring**: plugin enabled *and* route mapping *and* the required env vars.
5. **Flags drift**: when the skill snapshot and the live docs differ, the agent says so and cites the page URL it fetched. It fetches the live page whenever precision matters (exact config fields, endpoint lists, signatures) or when a plugin is marked "not captured" / "summary only", rather than guessing.

The skill carries an explicit guardrail against inventing unsupported plugin config keys, endpoints, or capability names, and treats `authulaconfig.NewConfig(...)` / `authula.New(&authula.AuthConfig{...})` as the verified constructor forms.

## Files

- `SKILL.md` — entry point: modes, core mental model, minimal library skeleton, task→reference routing table, pitfalls, and answer rules.
- `references/setup.md` — full `config.toml` and `.env` key reference, Docker command, library-mode install/config/database/mount, a working email/password + sessions example, and curl tests.
- `references/routing-and-security.md` — route mappings (fields, path forms, merge behaviour), disabled paths, the mappings-vs-disabled-paths distinction, a security-model summary table, and the event bus.
- `references/extending.md` — router adapters, custom routes and `RequestContext`, request hooks (stages, struct, rules), service hooks, and the programmatic API.
- `references/custom-plugins.md` — the `Plugin` interface, `PluginContext`, optional capability interfaces, a step-by-step example plugin, TOML config, and best practices.
- `references/plugins.md` — plugin index with live doc URLs, per-plugin details for session/email/email-password/oauth2/totp, and links to the config, database schema, email template, SDK, playground, and pkg.go.dev pages.

## Example prompts

```text
Create a standalone Authula setup with PostgreSQL, email-password, and sessions.
Protect the /me endpoint and include config.toml and .env.example.
```

```text
Add Authula to this Go backend with GitHub OAuth and session authentication,
mounting the handler under /api/auth on Chi.
```

```text
My Authula TOTP verify endpoint returns 401. Check the route mappings and fix
the pending-token flow.
```

```text
Write a custom Authula plugin that adds a GET /api/my-plugin/info route and
loads its options from [plugins.my_plugin].
```

## Install

```sh
./install.sh --target claude --skill authula /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

The guidance was authored for this repository and describes the Authula project ([github.com/Authula/authula](https://github.com/Authula/authula), docs at [authula.dev/docs](https://authula.dev/docs)). No LICENSE file is bundled with this skill.