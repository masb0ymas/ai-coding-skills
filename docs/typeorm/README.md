# TypeORM

TypeORM is a decorator-based ORM for TypeScript and JavaScript that supports both the **Data Mapper** pattern (repositories and `EntityManager`) and the **Active Record** pattern (`extends BaseEntity`) ([typeorm.io](https://typeorm.io), repo [typeorm/typeorm](https://github.com/typeorm/typeorm)). It runs on Node.js and works with PostgreSQL, MySQL, MariaDB, SQLite, SQL Server, Oracle, SAP HANA, Spanner, CockroachDB, and MongoDB. This skill is a condensed snapshot of the official docs, written for this repository and verified against **TypeORM v1.1** by typechecking every documented pattern against the real package.

## When to use it

- The user mentions TypeORM or typeorm.io.
- Code imports from `typeorm`, or uses `reflect-metadata` alongside entity classes.
- Defining entities or columns: `@Entity`, `@Column`, primary keys, generated columns, enums, embedded entities, inheritance, tree entities, entity schemas.
- Setting up a `DataSource`, or deciding between `synchronize` and migrations.
- Writing relations: one-to-one, one-to-many, many-to-many, `@JoinColumn`, `@JoinTable`, cascade behavior, eager/lazy loading, orphaned rows.
- Using repositories, `EntityManager`, find options, or find operators.
- Writing `QueryBuilder` queries: select, insert, update, delete, joins, parameters, pagination, subqueries, locking, relational queries.
- Working with transactions or isolation levels, or the migration generate/run/revert workflow.
- Listeners, subscribers, caching, logging, custom repositories, naming strategies, or debugging TypeORM errors.
- Not for: other ORMs (Prisma, Drizzle, MikroORM, Sequelize). The skill does not guess option lists that its references do not cover — it fetches the live page instead.

## What it covers

### Setup non-negotiables

- Install `typeorm` plus `reflect-metadata` and a driver (`pg`, `mysql2`, `better-sqlite3`, `mssql`, `mongodb`).
- Import `reflect-metadata` once at the very top of the app entry, before any entity import.
- Enable `emitDecoratorMetadata` and `experimentalDecorators` in `tsconfig.json`.
- Scaffold with `npx typeorm init --name MyProject --database postgres` (`--docker`, `--express`, `--module esm` available).
- Every entity must be registered in the `DataSource` (explicitly or via glob), and `initialize()` must run once at bootstrap.

### Rules that prevent most TypeORM bugs

- **Never ship `synchronize: true` to production** — it auto-syncs the schema on every launch and can lose data. Use migrations.
- **`save()` is not a bulk insert.** It runs a transaction, listeners, cascades, and returns the entity. For bulk writes use `insert()`, `update()`, or `upsert()` — faster, but they skip listeners, cascades, and entity reloads.
- **Relations are not loaded by default.** Pass `relations: { photos: true }` or use QueryBuilder `leftJoinAndSelect`. Eager relations load with `find*` but are ignored by QueryBuilder.
- **Never initialize relation arrays** (`photos: Photo[] = []`) — TypeORM treats a loaded `[]` as "all relations removed" and detaches existing rows on save.
- **Cascade saves only flow from the side you set** — setting the inverse side does nothing.
- **QueryBuilder parameters must be uniquely named**; reusing `:id` with different values overrides silently.
- **`skip`/`take` ≠ `limit`/`offset`** — `skip`/`take` are entity-aware and correct with joined one-to-many; `limit`/`offset` limit raw rows. On MSSQL, `take` requires an `order`.
- **In transactions, use the manager you are given** — `dataSource.transaction(async (em) => ...)`; global managers run outside the transaction.
- **ESM projects** should wrap relation property types in `Relation<T>` to avoid circular-import issues.

### Reference areas

| Area | What it covers |
| --- | --- |
| DataSource & entities | `new DataSource()`, options, entity and column decorators, primary keys, special columns, enums, embedded/inheritance/tree entities, entity schemas |
| Relations | All four relation decorators, owner side, `@JoinColumn`/`@JoinTable`, cascade, eager/lazy, orphaned rows, FAQ gotchas |
| Repository & find options | Repository/Manager API, `save` vs `insert`/`update`/`upsert`, soft deletes, every find option and operator |
| QueryBuilder | Select/insert/update/delete builders, joins, parameters, pagination, subqueries, locking, relational QueryBuilder |
| Transactions & migrations | `transaction()` with isolation levels, QueryRunner, the migration generate/run/revert workflow |
| Advanced | Listeners/subscribers, caching, logging, Active Record, custom repositories, naming strategies, MongoDB |

## How it works

The skill is a task-routed reference set. The agent reads the reference that matches the task (per the routing table in `SKILL.md`) before writing non-trivial code in that area, applies the setup non-negotiables when scaffolding, and reaches for the "rules that prevent most bugs" list whenever the task touches relations, bulk writes, transactions, or pagination. For exact option lists beyond the snapshot it fetches the live page linked in each reference rather than trusting memory.

## Files

- `SKILL.md` — entry point: setup non-negotiables, a minimal entity plus repository example, the bug-prevention rules, and live-doc links.
- `references/datasource-and-entities.md` — `DataSource` options, entity and column decorators, primary keys, special columns, enums, embedded/inheritance/tree entities, entity schemas.
- `references/relations.md` — the four relation types, owner side, join columns and tables, cascade, eager/lazy, orphaned rows, and relation gotchas.
- `references/repository-and-find-options.md` — repository and manager API, `save` versus `insert`/`update`/`upsert`, soft deletes, and the full find-options and operators reference.
- `references/query-builder.md` — select, insert, update, and delete builders; joins; parameters; pagination; subqueries; locking; relational QueryBuilder.
- `references/transactions-and-migrations.md` — `transaction()` with isolation levels, QueryRunner, and the migration generate/run/revert workflow.
- `references/advanced.md` — listeners and subscribers, caching, logging, Active Record, custom repositories, naming strategies, MongoDB.

## Example prompts

```text
Set up TypeORM with PostgreSQL for this NestJS app — DataSource config, entities,
and a migration instead of synchronize.
```

```text
Add a many-to-many relation between Post and Tag, and show how to load it with
both find options and QueryBuilder.
```

```text
My TypeORM save() is deleting rows from a related table. Figure out why.
```

```text
Write a transaction that transfers a balance between two accounts with the
serializable isolation level and retries on conflict.
```

## Install

```sh
./install.sh --target claude --skill typeorm /path/to/project
```

`--target` defaults to `all` (install for every supported agent); `--target agents|claude|openclaude|zcode` selects one.

## Source and license

The guidance was authored for this repository and condenses the official TypeORM documentation ([typeorm.io](https://typeorm.io); docs markdown lives in [typeorm/typeorm](https://github.com/typeorm/typeorm) under `docs/docs/`). No LICENSE file is bundled with this skill.
