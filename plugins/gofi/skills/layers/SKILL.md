---
name: layers
description: Keep a gofi-style Go codebase inside its layers (cmd, internal/app, config, dtos, lib, middlewares, models, handlers, repositories, seeders, migrations) when adding or changing features. Use for adding a resource/endpoint/table/field, CRUD module, migration, seeder, middleware or config in a Fiber+PostgreSQL project with this layout, "add a feature/endpoint/table", or to audit layer violations.
---

# gofi:layers — working inside the layers

Every change in a gofi project must land in the right layer. This skill
contains each layer's contract, a CRUD generator, and an automated audit. If the
structure does not exist yet, use `gofi:scaffold` first.

## Layer contracts (summary)

| Layer                   | Job                                                                                                      | Must not                                           |
| ----------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `cmd/api`               | wiring, `server.go` (global middleware), `routes.go` (all routes), `flag.go` (env → config + validation) | business logic, SQL                                |
| `cmd/migrate`           | migration/seed CLI                                                                                       | —                                                  |
| `internal/config`       | Config struct + constants                                                                                | read env/flags (that belongs in `cmd/api/flag.go`) |
| `internal/app`          | `Application` = dependency container                                                                     | any logic                                          |
| `internal/models`       | table row structs, embed `Base` (+`SoftDelete`), `db`+`json` tags                                        | import fiber / internal layers                     |
| `internal/dtos`         | `XBody`/query + `Validate(v *validator.MapValidator)`, response helpers                                  | `database/sql`, models, repositories               |
| `internal/repositories` | one `XRepository{BaseRepository}` per table; parameterized SQL                                           | fiber, dtos, handlers                              |
| `internal/handlers`     | bind+validate → repository → `dtos.*`; return `error`                                                    | SQL, `database/sql`, writing error JSON itself     |
| `internal/middlewares`  | cross-route concerns (auth, role, rate limit, CSRF, idempotency, error)                                  | per-resource logic                                 |
| `internal/lib`          | generic utils: `apperr`, `validator`, `constant`, DB/transactions, context                               | import the layers above it                         |
| `internal/seeders`      | idempotent `Seeder{Name(),Seed()}` via `runSeed`                                                         | —                                                  |
| `migrations`            | `NNNNNN_name.up.sql` + `.down.sql`, embedded                                                             | editing migrations that are already deployed       |

Dependency direction: `handlers → repositories → models`, `handlers → dtos → lib/validator`,
everything may use `lib/*`; `app` only uses `config` + `repositories`. Full details
and code examples: `references/patterns.md`. In the references, `<plugin-root>` means
`${CLAUDE_PLUGIN_ROOT}`.

## Workflow for adding a feature

1. **Understand first.** Read the closest example file (the `categories` module is
   the canonical reference) and `cmd/api/routes.go`. Follow the repo's comment style:
   explain _why_, use `ponytail:` for deliberate limitations.
2. **New CRUD resource → use the generator** (Python stdlib):
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/layers/scripts/new_resource.py --root . --name product \
     --fields "name:string:required:max=150,price:int:required,description:text,category_id:uuid:ref=categories" \
     --access superuser
   ```

   - types: `string text int float bool uuid time`; flags: `required`, `max=N`,
     `ref=table`, `unique`. Non-required fields → pointer (`*T`) and a NULL column.
   - `--access superuser` (public read, super-user write — default),
     `auth` (write: any logged-in user), `private` (every route requires login).
     Neither scopes rows to their owner: any signed-in user can read and change
     every row. For per-user data follow `references/patterns.md` §4.
   - `--no-soft-delete`, `--table`, `--path`, `--search`, `--dry-run`, `--no-routes`.
     The generator writes the migration, model, dto (+test), repository, and handler,
     registers them in both `factory.go` files, adds routes to `routes.go`, and
     adds the `Integer/Number/Bool` validator rules if missing. Afterwards,
     adjust what the generator cannot guess (composite unique constraints,
     default values, per-user ownership, fields that must not be changed).
3. **Non-CRUD changes → by hand**, following the recipes in `references/patterns.md`:
   adding a column, custom action endpoints, multi-table transactions, user-owned
   resources (`user_id` from `lib.ContextGetUID`), new middleware, seeders,
   constants, new config/env.
4. **Migrations are always new files.** Never edit/renumber a migration that may
   already have been applied in any environment. Create one with
   `make db/migrations/new name=add_x_to_y` (needs the `migrate` CLI) or copy
   the pattern with the next number; write a `down` that truly reverses `up`.
5. **Verify**:
   ```sh
   gofmt -l . && go build ./... && go vet ./... && go test ./...
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/layers/scripts/audit_layers.py --root .
   make db/migrations/up   # if a local DB is available
   ```
   `audit_layers.py` fails (exit 1) on forbidden cross-layer imports, raw SQL
   outside repositories/seeders, and unpaired migrations, and warns
   about types not yet registered in a factory.
6. **Documentation**: new env → `.env.example` + README table; new endpoints
   whose behavior is not obvious from the code → README.

## Hard rules

- Errors are always `return err`; use `apperr.New(apperr.KindX, ...)` or a
  sentinel (`apperr.ErrNotFound`, …). `middlewares.ErrorHandler` renders them.
  Validation errors → 422 automatically via `lib.ValidateRequestBody/Query`.
- SQL is always parameterized (`$1..$n`). `ORDER BY` only via `resolveOrder` +
  a whitelist; `ILIKE` via `whereBuilder.search` (already escapes wildcards).
- Responses only via `dtos.List/Get/OK/Created/Message/Response`.
- New IDs: `uuid.NewV7()` in the handler; re-read after insert/update so the
  DB timestamps are included in the response.
- Write routes: `m.Authorization` → (`m.SuperUser`) → `idempotent` → handler;
  this order matters (idempotency needs the UID).
- Repository writes that touch no rows → `requireAffected` (404).
- Do not add new dependencies without a strong reason; stdlib + existing ones first.
