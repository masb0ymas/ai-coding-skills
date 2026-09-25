# TypeORM DataSource & Entities

Source: https://typeorm.io/docs/data-source/data-source and https://typeorm.io/docs/entity/entities

## DataSource

Holds connection settings + the connection pool. Create it once, export it, `initialize()` at bootstrap, and never `destroy()` in a long-running server.

```ts
import { DataSource } from "typeorm"

export const AppDataSource = new DataSource({ /* options */ })
try {
  await AppDataSource.initialize() // establishes pool, registers entities, syncs schema if enabled
} catch (error) {
  console.error("Error during Data Source initialization", error)
}
```

Access points: `AppDataSource.manager` (EntityManager for all entities), `AppDataSource.getRepository(Entity)`, `AppDataSource.query(sql)`, `AppDataSource.transaction(cb)`, `AppDataSource.createQueryRunner()`. Multiple DataSources are fine (one per database).

## DataSourceOptions essentials

| Option | Notes |
| --- | --- |
| `type` | required: `postgres`, `mysql`, `mariadb`, `sqlite`, `better-sqlite3`, `mssql`, `oracle`, `mongodb`, `cockroachdb`, `sap`, `spanner`, `sqljs`, `expo`, `react-native`, `aurora-mysql`, `aurora-postgres`, ... |
| `entities` | classes and/or globs: `[Photo, "entities/**/*{.js,.ts}"]` |
| `subscribers`, `migrations` | same: classes or globs |
| `synchronize` | auto-create schema per launch. **Dev/debug only — data loss risk in production.** No-op for MongoDB (indexes only) |
| `logging` | `true`, or `["query", "error", "schema"]`, or a custom `logger`; loggers: `advanced-console` (default), `formatted-console`, `simple-console`, `file` |
| `maxQueryExecutionTime` | ms threshold to log slow queries |
| `poolSize` | max active connections in the pool |
| `dropSchema` | drop schema each init — dev only |
| `migrationsRun` | auto-run pending migrations on launch |
| `migrationsTableName` | default `"migrations"` |
| `cache` | enable result caching; `{ type: "redis", options: {...} }` |
| `namingStrategy` | custom table/column naming |
| `entityPrefix` | prefix all table names |
| `isolationLevel` | default isolation for all transactions |
| `invalidWhereValuesBehavior` | control null/undefined in where: `{ null: 'ignore'|'sql-null'|'throw', undefined: 'ignore'|'throw' }` (defaults throw) |

## Entity basics

Each entity = one table; must have at least one primary column. Column types are inferred from TS types (`string`→varchar(255), `number`→int, `boolean`, `Date`); override explicitly.

```ts
import { Entity, PrimaryGeneratedColumn, Column } from "typeorm"

@Entity()
export class Photo {
  @PrimaryGeneratedColumn()
  id: number

  @Column({ length: 100 })
  name: string

  @Column("text")
  description: string

  @Column("double")
  views: number

  @Column({ default: false })
  isPublished: boolean
}
```

- `@PrimaryColumn()` — manual PK; `@PrimaryGeneratedColumn()` — auto-increment/serial; `@PrimaryGeneratedColumn("uuid")` — generated uuid; `"rowid"` (Oracle), `"identity"` (Postgres/MSSQL). Composite PKs: multiple `@PrimaryColumn()`.
- Table name: class name (snake-cased per naming strategy); override with `@Entity({ name: "photos" })`.

## Special columns

| Decorator | Behavior |
| --- | --- |
| `@CreateDateColumn` | auto-set insertion date |
| `@UpdateDateColumn` | auto-set on every `save`/upsert-update |
| `@DeleteDateColumn` | auto-set by `softDelete`/`softRemove`; non-null rows are excluded from default scope |
| `@VersionColumn` | auto-incremented number on each save (optimistic locking) |

## Column options (on `@Column`)

`type`, `name` (db column name), `length`, `nullable` (**default false** → NOT NULL), `default`, `unique`, `primary`, `comment`, `precision`/`scale` (decimal), `unsigned` (MySQL), `charset`/`collation`, `enum`/`enumName`, `array` (Postgres arrays), `select: false` (hide from default queries), `insert: false`/`update: false` (write-once columns), `onUpdate` (MySQL), `asExpression`+`generatedType` (generated columns), `transformer: { to, from }` (marshal on read/write; array of transformers supported), `utc` (date columns).

## Handy column types

- `@Column({ enum: Role, type: "enum" })` or `@Column("simple-enum", { enum: Role })` — enums
- `@Column("simple-array")` — string[] stored comma-separated; `@Column("simple-json")` — object stored as JSON string
- `@Column({ type: "jsonb" })` (Postgres) — real JSON; query with `JsonContains` etc.
- `@Column({ type: "vector", dimensions: 3 })` — pgvector-style vector columns
- `@Column({ type: "geometry" })` — spatial columns
- `@Index()`, `@Index("idx_name", ["col1", "col2"], { unique: true })` on class; `@Unique` constraints

## Beyond plain entities

- **Embedded entities**: `@Column(() => Name)` with `@Column()` fields inside — columns flattened into the same table.
- **Entity inheritance**: concrete table inheritance (`extends`) + `@ChildEntity()`; single-table via `@TableInheritance({ column: { name: "type" } })` with `@ChildEntity("discriminator")`.
- **Tree entities**: `@Tree("adjacency-list" | "closure-table" | "materialized-path" | "nested-set")` + `@TreeParent()`/`@TreeChildren()`; use `TreeRepository` (`findTrees()`, `findDescendantsTree()`...).
- **View entities**: `@ViewEntity({ expression: (dataSource) => qb.getQuery() })` — mapped read-only views.
- **Entity schemas** (`separating entity definition`): define entities without decorators (useful in plain JS) via `EntitySchema`.
- **ESM**: use `Relation<T>` from typeorm for relation property types.
