---
name: typeorm
description: Best practices and API reference for TypeORM (typeorm.io), the TypeScript/JavaScript ORM for Postgres, MySQL, MariaDB, SQLite, SQL Server, Oracle, SAP HANA, Spanner, CockroachDB, and MongoDB. Use when defining entities or columns, setting up a DataSource, writing relations (one-to-one, one-to-many, many-to-many), using repositories or EntityManager, find options and operators, QueryBuilder queries, transactions, migrations, listeners/subscribers, soft deletes, upserts, custom repositories, or debugging TypeORM errors. Trigger whenever code imports from "typeorm" or the user mentions TypeORM, even if they don't say "best practices".
---

# TypeORM

TypeORM is a decorator-based ORM using both **Data Mapper** (repositories/manager) and **Active Record** (`extends BaseEntity`) patterns. Runs on Node.js and friends; TypeScript-first but also usable from JavaScript (ES2021).

This skill is a condensed snapshot of the official docs (TypeORM v1.1, verified September 2026 — API is the same `DataSource`-based one introduced in 0.3). For exact option lists beyond what's here, fetch the live page linked in each reference instead of trusting memory.

## References

| Area | Resource | When to Use |
| --- | --- | --- |
| DataSource & Entities | `references/datasource-and-entities.md` | `new DataSource()`, options, entity/column decorators, primary keys, special columns, enums, embedded/inheritance/tree entities, entity schemas |
| Relations | `references/relations.md` | `@OneToOne/@ManyToOne/@OneToMany/@ManyToMany`, owner side, `@JoinColumn`/`@JoinTable`, cascade, eager/lazy, orphaned rows, FAQ gotchas |
| Repository & Find Options | `references/repository-and-find-options.md` | Repository/Manager API, `save` vs `insert`/`update`/`upsert`, soft deletes, all find options and operators |
| QueryBuilder | `references/query-builder.md` | Select/insert/update/delete QB, joins, parameters, pagination, subqueries, locking, relational QB |
| Transactions & Migrations | `references/transactions-and-migrations.md` | `transaction()` with isolation levels, QueryRunner, migration generate/run/revert workflow |
| Advanced | `references/advanced.md` | Listeners/subscribers, caching, logging, Active Record, custom repositories, naming strategies, MongoDB |

Read the relevant reference before writing non-trivial code in that area. The essentials are below.

## Setup non-negotiables

```sh
npm install typeorm reflect-metadata   # + a driver, e.g. pg, mysql2, better-sqlite3, mssql, mongodb
```

1. **Import `reflect-metadata` once, at the very top** of the app entry (before any entity import).
2. **`tsconfig.json` must enable** `"emitDecoratorMetadata": true` and `"experimentalDecorators": true`.
3. Scaffold with `npx typeorm init --name MyProject --database postgres` (add `--docker`, `--express`, `--module esm`).

```ts
import "reflect-metadata"
import { DataSource } from "typeorm"
import { Photo } from "./entity/Photo"

export const AppDataSource = new DataSource({
  type: "postgres",
  host: "localhost",
  port: 5432,
  username: "test",
  password: "test",
  database: "test",
  entities: [Photo],            // every entity must be registered here (or via glob)
  synchronize: true,            // DEV ONLY — see below
  logging: false,
})

await AppDataSource.initialize() // once at bootstrap; throws on failure
```

## Minimal entity + repository

```ts
import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from "typeorm"

@Entity()
export class Photo {
  @PrimaryGeneratedColumn()
  id: number

  @Column({ length: 100 })
  name: string

  @Column("text", { nullable: true })
  description: string

  @CreateDateColumn()
  createdAt: Date
}

const photoRepository = AppDataSource.getRepository(Photo)
await photoRepository.save(photoRepository.create({ name: "Me and Bears" }))
const recent = await photoRepository.find({
  where: { name: "Me and Bears" },
  order: { createdAt: "DESC" },
  take: 10,
})
```

## Rules that prevent most TypeORM bugs

**Never ship `synchronize: true` to production** — it auto-syncs schema from entities on every launch and can lose data. Use migrations instead (Transactions & Migrations ref); set `synchronize: false` and `migrationsRun: true` or run `migration:run` in CI.

**`save()` is not a bulk insert.** `save()` runs a transaction, listeners/subscribers, and cascades, and returns the entity (id set). For bulk/high-throughput writes use `insert()`, `update()`, or `upsert()` — they're faster but skip listeners, cascades, and entity reloads.

**Relations are NOT loaded by default.** Every `find*` returns relations as `undefined` unless you pass `relations: { photos: true }` or use QueryBuilder `leftJoinAndSelect`. Eager relations load automatically with `find*` but are ignored by QueryBuilder.

**Never initialize relation arrays** (`photos: Photo[] = []` or in the constructor) — TypeORM treats a loaded `[]` as "all relations removed" and will detach existing rows on `save()`.

**Cascade saves only flow from the side you set.** With `cascade: true` on `photo.metadata`, setting `photo.metadata = m` and saving `photo` cascades — setting the inverse side does not.

**QueryBuilder parameters must be uniquely named.** Using `:id` twice with different values overrides silently — use `:sheepId`/`:cowId` (see QueryBuilder ref).

**`skip`/`take` ≠ `limit`/`offset`.** `skip`/`take` are entity-aware pagination (correct with joined one-to-many); `limit`/`offset` limit raw rows and break under joins. On MSSQL, `take` requires an `order`.

**In transactions, use the manager you're given.** `dataSource.transaction(async (em) => ...)` — all queries inside must go through `em`; global managers/repositories are outside the transaction.

**ESM projects:** wrap relation property types in `Relation<T>` (`photo: Relation<Photo>`) to avoid circular-import issues.

## Verify against live docs when precision matters

| Topic | Page |
| --- | --- |
| Getting started | https://typeorm.io/docs/getting-started |
| Entities & columns | https://typeorm.io/docs/entity/entities |
| Relations | https://typeorm.io/docs/relations/relations |
| Find options | https://typeorm.io/docs/working-with-entity-manager/find-options |
| Repository API | https://typeorm.io/docs/working-with-entity-manager/repository-api |
| Select QueryBuilder | https://typeorm.io/docs/query-builder/select-query-builder |
| Transactions | https://typeorm.io/docs/transactions |
| Migrations | https://typeorm.io/docs/migrations/setup |
