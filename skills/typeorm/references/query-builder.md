# TypeORM QueryBuilder

Source: https://typeorm.io/docs/query-builder/select-query-builder (plus insert/update/delete/relational pages)

## Creating and executing

Three equivalent entry points:

```ts
dataSource.createQueryBuilder().select("user").from(User, "user")...
dataSource.manager.createQueryBuilder(User, "user")...
dataSource.getRepository(User).createQueryBuilder("user")... // most common
```

Five QB types: `.select()`/`getRepository(...)` default, `.insert().into(Entity)`, `.update(Entity).set({...})`, `.delete().from(Entity)`, and relational QB (`.relation()`).

Terminators: `getOne()`, `getOneOrFail()`, `getMany()`, `getManyAndCount()`, `getCount()`, `getRawOne()`, `getRawMany()`, `stream()`, `execute()` (insert/update/delete). Debug with `.getSql()` / `.printSql()`.

## Parameters — always, and uniquely named

```ts
.where("user.name = :name", { name: "Timber" })          // escapes → no SQL injection
.where("user.name IN (:...names)", { names: ["a", "b"] }) // array expansion
.setParameter("name", "Timber")
```

**Never interpolate user input into the SQL string.** Parameter names are global per QB — reusing `:id` for two different values silently overrides; use `:sheepId` / `:cowId`.

## WHERE building

`.where()` replaces the whole expression; chain `.andWhere()` / `.orWhere()` to append. Group with `Brackets`:

```ts
import { Brackets } from "typeorm"

qb.where("user.isActive = :active", { active: true })
  .andWhere(new Brackets((qb2) => {
    qb2.where("user.firstName = :f", { f: "Timber" }).orWhere("user.lastName = :l", { l: "Saw" })
  }))
```

Also: `.having()`, `.groupBy("user.id")`, `.orderBy("user.id", "DESC")`, `.addOrderBy(...)`, `.distinctOn(["user.name"])` (Postgres), `.limit()`, `.offset()`.

## Joins

- `leftJoinAndSelect(relationPath, alias, condition?, params?)` — join + select into entities (e.g. `"photo.metadata"`, alias `"metadata"`).
- `innerJoinAndSelect(...)` — drops parents with no match; `leftJoin`/`innerJoin` — filter without selecting.
- Join unrelated entities/tables too: `.leftJoinAndSelect(Photo, "photo", "photo.userId = user.id")`.
- Put join-only conditions in the 3rd argument (ON clause), not `.where()` — otherwise LEFT JOIN silently degrades to INNER.

## Pagination & locking

- `.skip(n).take(m)` — entity-aware (correct with one-to-many joins); `.limit()/.offset()` — raw rows.
- Lock modes (`findOne`-style queries): `{ mode: "optimistic", version }`, `"pessimistic_read"`, `"pessimistic_write"`, `"dirty_read"`, `"for_no_key_update"`, `"for_key_share"`, plus `tables` and `onLocked: "nowait" | "skip_locked"`.
- `.maxExecutionTime(ms)`, `.useIndex(...)`.

## Advanced select

- **Subqueries**: pass a nested QB into `.where(...)`/`.from()`.
- **CTEs**: `.addCommonTableExpression(qb, "alias")` / `.withCTE(...)`; recursive CTEs supported.
- `withDeleted: true` — include soft-deleted rows; hidden columns (`select: false`) need explicit select.
- `getRawMany()` returns raw rows with selected-expression keys — needed for aggregates (`COUNT`, `SUM`); call `.groupBy()` and alias expressions explicitly.

## Insert / Update / Delete QB

```ts
await dataSource.createQueryBuilder()
  .insert().into(User)
  .values([{ firstName: "Timber" }, { firstName: "Phantom" }])
  .orIgnore()                                            // skip rows that conflict
  .orUpdate(["firstName"], ["externalId"])               // (columns to update, conflict target); options: { overwriteCondition: {...} }
  .returning(["id"])                                     // RETURNING/OUTPUT-capable drivers (verified in type defs)
  .execute()

await dataSource.createQueryBuilder()
  .update(User).set({ name: "New" })
  .where("id = :id", { id: 1 }).execute()

await dataSource.createQueryBuilder()
  .delete().from(User).where("isActive = :active", { active: false }).execute()
```

## Relational QueryBuilder (link rows without loading entities)

```ts
await dataSource.createQueryBuilder()
  .relation(User, "photos")
  .of(userId)
  .add(photoOrId)          // also .remove(...), .set(...) (replaces, for one/one-to-many), .addAndSave / .removeAndSave
```

## Caching

`.cache(true)`, `.cache(60000)`, or `.cache("my-key", 60000)` — requires `cache` enabled in DataSource options; invalidate with `queryResultCache.remove(["my-key"])` / `.clear()`.
