# TypeORM Transactions & Migrations

Source: https://typeorm.io/docs/transactions and https://typeorm.io/docs/migrations/setup (+ sibling pages)

## Transactions

### Callback style (default choice)

```ts
await AppDataSource.transaction(async (transactionalEntityManager) => {
  await transactionalEntityManager.save(users)
  await transactionalEntityManager.save(photos)
})
```

- **Always use the provided manager inside the callback** — the global `AppDataSource.manager`/repositories run outside the transaction.
- Isolation level as first argument: `transaction("SERIALIZABLE", cb)`. Supported set varies by driver (Postgres/MySQL/MariaDB/MSSQL: READ UNCOMMITTED → SERIALIZABLE, MSSQL also SNAPSHOT; Oracle: READ COMMITTED/SERIALIZABLE; SQLite: effectively SERIALIZABLE). Unsupported levels throw.
- DataSource-wide default: `new DataSource({ isolationLevel: "SERIALIZABLE" })`.
- Custom repositories must be re-scoped inside transactions: `transactionalEntityManager.withRepository(UserRepository)`.

### QueryRunner style (manual control)

```ts
const queryRunner = AppDataSource.createQueryRunner()
await queryRunner.connect()
await queryRunner.startTransaction()
try {
  await queryRunner.manager.save(user1)
  await queryRunner.commitTransaction()
} catch (err) {
  await queryRunner.rollbackTransaction()
} finally {
  await queryRunner.release() // required for manually created runners
}
```

## Migrations

Migrations replace `synchronize` in production. Each migration = class with `up()` and `down()`.

### Setup

```ts
export default new DataSource({
  synchronize: false,                                  // essential once you use migrations
  migrations: [__dirname + "/migrations/**/*{.js,.ts}"], // classes or globs
  migrationsRun: false,                                // or auto-run on launch
  migrationsTableName: "migrations",
  migrationsTransactionMode: "all",                    // "all" | "each" | "none"
})
```

### Workflow

```sh
# 1. change your entities, then generate a migration (diffs entities vs DB; exits 1 if no change)
npx typeorm migration:generate -d src/data-source.ts PostRefactoring
# or with ts-node runners:
npx typeorm-ts-node-esm migration:generate ./src/migrations/PostRefactoring -d ./src/data-source.ts

# 2. create an empty migration (hand-written changes)
npx typeorm migration:create ./src/migrations/AddIndexOnPosts

# 3. run pending migrations (ordered by timestamp)
npx typeorm migration:run -d src/data-source.ts      # ts-node: typeorm-ts-node-commonjs / -esm

# 4. revert the last executed migration
npx typeorm migration:revert -d src/data-source.ts

# also: migration:show (list status), migration:faking / migration:unfaking (mark as run without executing)
```

Gotchas:

- `migration:run`/`revert` execute **.js** files; compile first, or use the `typeorm-ts-node-esm`/`typeorm-ts-node-commonjs` wrappers for .ts.
- Generated file names embed a timestamp class suffix — don't rename the class suffix.
- Generated migrations are safe to edit before running; the rule of thumb is to generate after **each** entity change.
- A migration skeleton looks like:

```ts
import { MigrationInterface, QueryRunner } from "typeorm"

export class PostRefactoringTIMESTAMP implements MigrationInterface {
  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`ALTER TABLE "post" RENAME COLUMN "title" TO "name"`)
  }
  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`ALTER TABLE "post" RENAME COLUMN "name" TO "title"`)
  }
}
```

- Keep `synchronize: true` in dev if you like, but once real data exists switch to `synchronize: false` + migrations everywhere so dev matches production.
