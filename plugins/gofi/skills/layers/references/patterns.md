# Recipes for changes inside the layers

All examples use the `product` resource produced by the generator. Rename as
needed. After each recipe: `gofmt -l . && go build ./... && go vet ./... &&
go test ./... && python3 <plugin-root>/skills/layers/scripts/audit_layers.py --root .`

## 1. Add a column to an existing table

1. New migration (never edit an old one):
   ```sql
   -- migrations/000006_add_sku_to_products.up.sql
   ALTER TABLE "products" ADD COLUMN IF NOT EXISTS "sku" VARCHAR;
   CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku ON "products" ("sku");
   -- migrations/000006_add_sku_to_products.down.sql
   DROP INDEX IF EXISTS idx_products_sku;
   ALTER TABLE "products" DROP COLUMN IF EXISTS "sku";
   ```
   A `NOT NULL` column on a table that already has data needs a `DEFAULT` or a backfill first.
2. `models/product.go`: `SKU *string \`db:"sku" json:"sku"\``.
3. `repositories/product.go`: add it to `productColumns`, `scanProduct`
   (order must match the columns), `Insert`/`Update` (column, placeholder, arg),
   and `productSortColumns` if it may be sorted on.
4. `dtos/product.go`: field `SKU *string \`json:"sku"\`` + `v.Field("sku").String().MaxLen(...)`.
5. `handlers/product.go`: `toProduct` maps `SKU: body.SKU`.
6. A unique violation (SQLSTATE `23505`) currently becomes a 500. If you need a 409,
   add a helper in `repositories/helpers.go` modeled on `translateForeignKey`:
   ```go
   const pgUniqueViolation = "23505"

   func translateUnique(err error, message string) error {
   	var pgErr *pgconn.PgError
   	if errors.As(err, &pgErr) && pgErr.Code == pgUniqueViolation {
   		return apperr.New(apperr.KindConflict, "%s", message)
   	}
   	return err
   }
   ```

## 2. Custom action endpoint (`PUT /v1/products/:id/publish`)

```go
// repositories/product.go
// Publish stamps published_at on a live product.
func (r *ProductRepository) Publish(ctx context.Context, id uuid.UUID) error {
	res, err := r.execContext(ctx, `
		UPDATE products
		SET published_at = now(), updated_at = now()
		WHERE id = $1 AND deleted_at IS NULL`,
		id,
	)
	if err != nil {
		return err
	}
	return requireAffected(res, "product")
}

// handlers/product.go
func (h *productHandler) Publish(c fiber.Ctx) error {
	return mutateByID(c, "product", h.repo().Publish, "product published")
}

// cmd/api/routes.go (inside the products block)
products.Put("/:id/publish", m.Authorization, m.SuperUser, idempotent, h.Product.Publish)
```
Registering a static route like `/:id/publish` after `/:id` is fine because the
segment counts differ; for sibling static paths (`/stats` vs `/:id`) register
the static one first.

## 3. Multi-table transactions

SQL stays in the repository. Use `lib.WithTransaction` (commit/rollback/panic
are already handled):

```go
// repositories/order.go
// Create inserts the order and its items atomically.
func (r *OrderRepository) Create(ctx context.Context, o models.Order, items []models.OrderItem) error {
	return lib.WithTransaction(ctx, r.DB, func(tx *sql.Tx) error {
		if _, err := tx.ExecContext(ctx,
			`INSERT INTO orders (id, user_id) VALUES ($1, $2)`, o.ID, o.UserID); err != nil {
			return err
		}
		for _, it := range items {
			if _, err := tx.ExecContext(ctx,
				`INSERT INTO order_items (id, order_id, quantity) VALUES ($1, $2, $3)`,
				it.ID, o.ID, it.Quantity); err != nil {
				return translateForeignKey(err, "a referenced record does not exist")
			}
		}
		return nil
	})
}
```
Importing `gofi/internal/lib` from repositories is allowed.

## 4. User-owned resources (per-user multi-tenancy)

1. Generate with an owner column and private access:
   `--fields "user_id:uuid:required:ref=users,..." --access private`
2. Remove `UserID` from `dtos.<X>Body` + its rule (clients must not choose the owner).
3. The handler fills the owner from the context:
   ```go
   uid, err := lib.ContextGetUID(c)
   if err != nil {
   	return apperr.ErrUnauthorized
   }
   item.UserID = uid
   ```
4. Repository: every `List/Count/Get/Update/Delete` takes an `ownerID` and
   adds a filter, e.g. in the filter builder:
   ```go
   func noteFilters(ownerID uuid.UUID, p ListParams) *whereBuilder {
   	w := newWhere(`deleted_at IS NULL`)
   	w.add("user_id = $%d", ownerID)
   	w.search(p.Search, "title")
   	return w
   }
   ```
   and `WHERE id = $1 AND user_id = $2` for by-id queries. Rows owned by another user
   become 404 (not 403) so their existence does not leak.

## 5. Extra list filters

```go
// dtos/product.go
type ProductQuery struct {
	ListQuery
	CategoryID string `query:"category_id"`
}

func (dto ProductQuery) Validate(v *validator.MapValidator) {
	dto.base(v) // the same offset/limit/search/sorted rules
	v.Field("category_id").Regex(`^[0-9a-fA-F-]{36}$`)
}
```
Handler: `var q dtos.ProductQuery` → `lib.ValidateRequestQuery(c, &q)` →
`q.Clamp()` → `listParams(q.ListQuery)`; pass `q.CategoryID` to the repository
as a separate parameter and add `w.add("category_id = $%d", id)` when it is
not empty. Add a query-binding test (embedded struct) in `lib`.

## 6. New middleware

- Needs app dependencies → a method on `*Middlewares` (`m.app.Repositories...`),
  like `SuperUser`.
- No dependencies → a constructor function `func X(cfg ...) fiber.Handler`, like
  `RateLimit`/`CrossOrigin`.
- Reject with `return apperr.ErrForbidden` / `apperr.New(...)`, continue with
  `return c.Next()`. Global → `server.go`; per route → `routes.go`.
- Write a unit test in `middlewares/x_test.go` (see `cross_origin_test.go`).

## 7. New seeder

```go
// seeders/product.go
type ProductSeeder struct{ DB *sql.DB }

func (s ProductSeeder) Name() string { return "product" }

// Seed inserts the fixed products; existing ids are left untouched.
func (s ProductSeeder) Seed() error {
	return runSeed(s.DB, func(ctx context.Context, tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx,
			`INSERT INTO "products" ("id", "name", "price", "is_active") VALUES ($1, $2, $3, $4) ON CONFLICT ("id") DO NOTHING`,
			constant.ProductStarterID, "Starter", 0, true)
		return err
	})
}
```
Fixed IDs live in `lib/constant/product.go`. Register it in `seeders.All` after
the seeders it references (e.g. after `CategorySeeder`).

## 8. Hiding / shaping response fields

- Fields that must never be exposed: `json:"-"` on the model.
- A different shape per endpoint: create a response struct in `dtos` and map it in the
  handler; the repository still returns the model.

## 9. Constants & roles

Roles/enums live in `lib/constant` (see `constant/user.go`), are validated in the DTO with
`Regex("^(a|b|c)$")`, and are enforced in the DB with a `CHECK` in the migration.
