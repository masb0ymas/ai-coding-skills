# TypeORM Advanced Topics

Source: https://typeorm.io/docs/listeners-and-subscribers, .../performance-optimization, .../guides/active-record-data-mapper, .../working-with-entity-manager/custom-repository

## Entity listeners (methods on the entity)

`@AfterLoad()`, `@BeforeInsert()`, `@AfterInsert()`, `@BeforeUpdate()`, `@AfterUpdate()`, `@BeforeRemove()`, `@AfterRemove()`, `@BeforeSoftRemove()`, `@AfterSoftRemove()`, `@BeforeRecover()`, `@AfterRecover()`.

Gotcha: `@BeforeUpdate`/`@AfterUpdate` only fire when something on the entity actually **changed** — a no-op `save()` skips them.

## Subscribers (cross-entity hooks)

```ts
import { EventSubscriber, EntitySubscriberInterface, InsertEvent } from "typeorm"
import { Post } from "../entity/Post"

@EventSubscriber()
export class PostSubscriber implements EntitySubscriberInterface<Post> {
  listenTo() {
    return Post // omit listenTo to listen to every entity
  }

  beforeInsert(event: InsertEvent<Post>) {
    console.log("BEFORE POST INSERTED:", event.entity)
  }
}
```

Register subscribers in the DataSource (`subscribers: [...]` or glob). Typical uses: validation (with class-validator), denormalization, audit logs.

## Caching (query result cache)

Enable in DataSource, then per query:

```ts
new DataSource({ /* ... */ cache: { type: "redis", options: { host: "localhost", port: 6379 } } })

await repo.find({ cache: true })                                  // default TTL
await repo.find({ cache: { id: "users-list", milliseconds: 25000 } })
await repo.createQueryBuilder("user").cache("users-list", 60000).getMany()
```

Invalidate by id: `AppDataSource.queryResultCache.remove(["users-list"])`. Cache lives per exact query; other drivers use the `typeorm_metadata`-backed local cache.

## Logging & slow queries

`logging: true | ["query" | "error" | "schema" | "migration" | "log"]`; custom logger classes implement the `Logger` interface; `maxQueryExecutionTime: 1000` logs any query slower than 1s — cheap production observability.

## Active Record vs Data Mapper

```ts
import { BaseEntity, Entity, PrimaryGeneratedColumn, Column } from "typeorm"

@Entity()
export class User extends BaseEntity {
  @PrimaryGeneratedColumn()
  id: number
  @Column()
  name: string
}

const user = new User(); user.name = "Timber"; await user.save()
const all = await User.find()
const first = await User.findOneBy({ id: 1 })
await user.remove()
```

Active Record puts persistence on the model (quick prototypes, small apps); Data Mapper (repositories) keeps entities clean of queries — better for larger, testable codebases. Both can coexist.

## Custom repositories

```ts
// 1. extend a repository instance (globally exported)
export const UserRepository = AppDataSource.getRepository(User).extend({
  findByName(firstName: string, lastName: string) {
    return this.createQueryBuilder("user")
      .where("user.firstName = :firstName", { firstName })
      .andWhere("user.lastName = :lastName", { lastName })
      .getMany()
  },
})

// inside transactions, re-scope it:
await AppDataSource.transaction(async (manager) => {
  const userRepository = manager.withRepository(UserRepository)
  await userRepository.findByName("Timber", "Saw")
})
```

## Performance optimization highlights

- Load only what you need: `select` projection + explicit `relations` (or `relationLoadStrategy: "query"` for wide one-to-many graphs).
- Avoid N+1: never `await` lazy relations inside loops; batch with `relations`/QueryBuilder joins.
- `save()` on large arrays does per-entity diffing — prefer `insert`/`update`/`upsert` for bulk.
- Index FK columns and every `where`/`order` hot path (`@Index()`); check generated SQL with `getSql()` and read `EXPLAIN` from the DB.
- Pagination: keyset (`where id > :after order by id take`) beats large `skip`.

## Other platforms & options

- **MongoDB**: `type: "mongodb"`, `@ObjectIdColumn`, `MongoRepository` (`find({ where: { ... } })` with Mongo operators, `aggregate`). `synchronize` only syncs indexes.
- **Naming strategies**: implement `NamingStrategyInterface` (or extend `DefaultNamingStrategy`) and pass via `namingStrategy`.
- **Multiple data sources**: create several `DataSource` instances (one per database); per-entity `@Entity({ database: "secondDB" })` / `@Entity({ schema: "..." })` targets other databases/schemas within one data source.
- **JavaScript (no TS)**: use `EntitySchema` definitions instead of decorators.
- **`sql` tagged template**: `import { sql } from "typeorm"` for parameterized raw SQL fragments.
- **Null/undefined in `where`**: by default TypeORM throws on `null`/`undefined` values passed into find-where objects — configure `invalidWhereValuesBehavior` if you want `ignore`/`sql-null` semantics.
