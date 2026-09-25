# TypeORM Repository, EntityManager & Find Options

Source: https://typeorm.io/docs/working-with-entity-manager/repository-api, .../find-options, .../working-with-repository

## Three ways to the same operations

| Pattern | Access | Notes |
| --- | --- | --- |
| Data Mapper (default) | `AppDataSource.getRepository(User)` or `AppDataSource.manager` | recommended for larger apps |
| Active Record | `class User extends BaseEntity` → `user.save()`, `User.find()` | queries live on the model |
| Custom repository | `getRepository(User).extend({...})` | domain-specific methods; see Advanced ref |

Repository flavors: `Repository`, `TreeRepository` (tree entities), `MongoRepository` (ObjectId-based).

## Write operations — know which one you need

| Method | Behavior |
| --- | --- |
| `save(entityOrEntities, opts?)` | insert-or-update per entity: **runs in a transaction**, fires listeners/subscribers, applies cascades, sets generated ids on the passed object, returns the same entity(ies) |
| `insert(payload)` | raw INSERT (plain object or array), returns `InsertResult` — no listeners, no cascades, no entity reload; fastest for bulk |
| `update(criteria, partial)` | raw UPDATE by id/conditions — no listeners; use `save` if subscribers must run |
| `upsert(payload, conflictPathsOrOptions, opts?)` | INSERT ... ON CONFLICT/ON DUPLICATE KEY UPDATE (Postgres, MySQL, SQLite, Cockroach...); `@UpdateDateColumn`/`@VersionColumn` update on conflict; `update: false` columns excluded; supports `returning` |
| `delete(criteria)` / `remove(entity)` | `delete` runs raw DELETE by criteria; `remove` takes loaded entities (fires listeners, cascades remove) |
| `softDelete(criteria)` / `restore(criteria)` | set/clear `@DeleteDateColumn` by id/conditions |
| `softRemove(entity)` / `recover(entity)` | soft-delete variants taking entities (fires listeners) |
| `preload(partial)` | merge plain object onto the loaded entity (combine with `save`) |
| `increment(criteria, column, n)` / `decrement(...)` | atomic column updates |
| `clear()` | TRUNCATE (respecting FKs) |

```ts
await repo.upsert(
  { externalId: "x", name: "New name" },
  { conflictPaths: ["externalId"], skipUpdateIfNoValuesChanged: true }
)
```

**Rule of thumb:** CRUD on loaded objects with business logic → `save`/`remove`. Bulk or hot-path writes → `insert`/`update`/`upsert`/`increment`.

## Read operations

`find`, `findBy(where)`, `findAndCount(By)`, `findOne(By)` (null when absent), `findOneOrFail` (throws `EntityNotFoundError`), `count(By)`, `exists(By)`, `query(sql)`, `createQueryBuilder(alias)`.

## Find options (accepted by all `find*`/`count` methods)

```ts
const users = await userRepository.find({
  select: { firstName: true, lastName: true },     // projection
  relations: {                                     // joins; nested supported
    profile: true,
    photos: { attributes: true },                  // photos.attributes sub-relation
  },
  relationLoadStrategy: "join",                    // "join" (default) | "query"
  loadEagerRelations: true,                        // set false to suppress eager relations
  where: {                                         // object = AND; array = OR
    lastName: "Saw",
    profile: { userName: "tshaw" },                // filter on joined relation
    age: MoreThan(18),
    firstName: Or(Equal("Timber"), ILike("tim%")),
  },
  order: { name: "ASC", id: "DESC" },
  skip: 5,                                         // entity-aware pagination — pair with take
  take: 10,
  withDeleted: true,                               // include soft-deleted rows
  cache: true,                                     // or { id, milliseconds }
  lock: { mode: "pessimistic_write", onLocked: "nowait" }, // findOne only
})
```

**Operators** (import from `typeorm`): `Not`, `LessThan`, `LessThanOrEqual`, `MoreThan`, `MoreThanOrEqual`, `Equal`, `Like`, `ILike`, `Between`, `In`, `Any`, `IsNull`, `ArrayContains`, `ArrayContainedBy`, `ArrayOverlap`, `JsonContains` (Postgres), `Raw((alias) => `${alias} > :date`, { date })` — compose with `And`, `Or`, `Not`.

**Pagination:** `skip`/`take` work correctly with joined one-to-many relations (they paginate entities, not raw rows); `limit`/`offset` (also available on QueryBuilder) apply to raw result rows and **break under joins**. On MSSQL, `take` requires `order`. For big offset pages prefer keyset pagination on an ordered indexed column.

**Soft deletes:** rows with a set `@DeleteDateColumn` are excluded from all queries unless `withDeleted: true`.

## EntityManager

Same API surface as a repository but entity-scoped per call: `manager.find(User, {...})`, `manager.getRepository(User)`, `manager.transaction(...)`, `manager.query(sql, params)`, `manager.createQueryRunner()`.
