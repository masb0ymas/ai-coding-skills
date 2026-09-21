# Postgres Best Practices

Guidance for working with PostgreSQL, covering schema design, indexing strategies, query optimization, migrations, and common pitfalls. The skill is authored for this repository and bundles a set of task-focused reference documents that the agent loads on demand, so advice stays concrete instead of generic. It targets PostgreSQL 14 through 18 and marks version-gated features so recommendations stay correct for the server actually in use.

## When to use it

- Writing or reviewing SQL, including CTEs, window functions, lateral joins, UPSERT/MERGE, and JSONB queries.
- Designing database schemas: tables, data types, primary/foreign keys, constraints, normalization, partitioning, multi-tenant layouts.
- Choosing and maintaining indexes: index types, composite column ordering, partial/covering/expression indexes, bloat and unused indexes.
- Optimizing a slow query with `EXPLAIN ANALYZE`, reading plan nodes, fixing bad row estimates or planner misconfigurations.
- Setting up or operating Postgres: performance diagnostics, locks, VACUUM, backup/restore, security and roles, bulk loading, connection pooling, replication, and major version upgrades.
- Deciding on transaction isolation levels and handling serialization failures.
- Not for other database engines; it is PostgreSQL-specific.

## What it covers

### Supported versions

PostgreSQL **14 through 18**. Version-specific features are tagged in the references — for example `[PG15+]` (`NULLS NOT DISTINCT`), `[PG16+]` (`pg_stat_io`), `[PG17+]` (`COPY ... ON_ERROR ignore`, `pg_createsubscriber`), and `[PG18+]` (built-in `uuidv7()`, `WITHOUT OVERLAPS` temporal constraints, `NOT ENFORCED` constraints, B-tree skip scan, swap-mode `pg_upgrade`, `REJECT_LIMIT`). Environment-dependent examples identify required privileges, extensions, or multi-node setup.

PostgreSQL provides 5 years of support per major version; always run the latest minor release.

| Version | Initial Release | End of Life |
| ------- | --------------- | ----------- |
| 18      | September 2025  | November 2030 |
| 17      | September 2024  | November 2029 |
| 16      | September 2023  | November 2028 |
| 15      | October 2022    | November 2027 |
| 14      | September 2021  | November 2026 |

Source: [postgresql.org/support/versioning](https://www.postgresql.org/support/versioning/)

### Main guidance areas

- **Schema design** — identity columns vs. UUIDs, `timestamptz`, `text` + `CHECK` over `varchar(n)`, naming conventions, FK actions and FK indexing, exclusion and temporal constraints, normalization vs. denormalization, partitioning, multi-tenant patterns, migration safety.
- **Indexing** — B-tree, GIN, GiST, BRIN, and hash indexes; composite column ordering; partial, covering (`INCLUDE`), and expression indexes; indexes on partitioned tables; `CREATE INDEX CONCURRENTLY`; reindexing, monitoring, and finding unused/duplicate indexes.
- **Query optimization** — running `EXPLAIN ANALYZE`, reading plans bottom-up, a plan-node reference (scans, joins, sorts, aggregates), join-strategy selection, common bottlenecks and their fixes.
- **Query patterns** — CTE materialization, window functions, `CROSS JOIN LATERAL` top-N-per-group, recursive queries, `INSERT ... ON CONFLICT` vs. `MERGE`, bulk operations, JSONB access and containment, date/time patterns, anti-patterns.
- **Performance diagnostics** — `pg_stat_*` views, table and index health, cache hit rates and `shared_buffers` tuning, missing FK indexes, active query analysis, lock analysis, VACUUM and bloat, connection management, `pg_stat_statements`.
- **Reliability and operations** — logical replication (pub/sub, CDC, live migration), physical streaming replication and failover, transaction isolation and retry logic, backup/restore and PITR, security and roles (privileges, RLS, `pg_hba.conf`, SSL), bulk loading, PgBouncer connection pooling, and major version upgrades.

## How it works

`SKILL.md` is a router plus a version policy. It lists the supported version range with release/EOL dates, then a **References** table mapping each guidance area to a reference file and the situations that should trigger it. The agent reads the skill, picks the reference document(s) matching the task, and applies their guidelines. Version-gated advice is tagged in place, so the agent can filter recommendations to the target server version, and environment-dependent examples state their privilege/extension/multi-node prerequisites up front. Each reference is self-contained and opens with a `Contents` list for fast navigation.

## Files

- `SKILL.md` — skill entry point: supported versions/EOL table and the references routing table.
- `references/schema-design.md` — data types, primary keys, foreign keys and referential integrity, check/exclusion/temporal constraints, normalization and denormalization, partitioning, multi-tenant patterns, migration safety.
- `references/indexing.md` — index types and when to use each (B-tree, GIN, GiST, BRIN, hash), composite column ordering, partial/covering/expression indexes, partitioned-table indexes, concurrent creation, maintenance, and finding unused/duplicate indexes.
- `references/query-optimization.md` — running and reading `EXPLAIN ANALYZE`, plan-node reference, join-strategy selection, common bottlenecks and fixes, statistics/planner tuning.
- `references/query-patterns.md` — CTEs, window functions, lateral joins, recursive queries, UPSERT/MERGE, bulk operations, JSONB queries, date/time patterns, and anti-patterns to avoid.
- `references/performance-diagnostics.md` — essential `pg_stat` views, table/index health checks, hit rates and `shared_buffers` tuning, active-query analysis, lock analysis, VACUUM and bloat, connection management, and `pg_stat_statements`.
- `references/logical-replication.md` — publisher/subscriber setup, publications and subscriptions management, replica identity, monitoring, schema changes during replication, live migration patterns, and troubleshooting.
- `references/hot-standby.md` — streaming replication overview, hot standby configuration, replication slots, lag monitoring, replication conflicts and delay settings, synchronous vs. asynchronous mode, and promoting a standby.
- `references/transaction-isolation.md` — isolation-level overview, READ COMMITTED (lost updates), REPEATABLE READ, SERIALIZABLE (SSI), common pitfalls, choosing a level, and serialization-failure retry patterns.
- `references/backup-restore.md` — backup strategy overview, logical backups (`pg_dump`/`pg_restore`), physical backups (`pg_basebackup`), point-in-time recovery, verification/testing, and automation patterns.
- `references/security-roles.md` — role management and predefined roles, the privilege system and default privileges, schema-based access control and `search_path` security, row-level security, `pg_hba.conf` authentication, password policies, and security best practices.
- `references/bulk-loading.md` — COPY vs. INSERT performance, `COPY FROM` patterns (file, STDIN, application code, `COPY TO`), load optimization (dropping indexes, disabling triggers/autovacuum, unlogged staging), ETL staging, and bulk updates/deletes.
- `references/connection-pooling.md` — why pooling matters, PgBouncer configuration and sizing, pool modes (transaction/session/statement), prepared-statement handling, monitoring/diagnostics, and application-side pooling.
- `references/major-version-upgrades.md` — upgrade-method comparison, `pg_upgrade` in-place upgrade step by step, logical-replication migration, `pg_createsubscriber`, and pre/post-upgrade checklists and testing strategy.

## Example prompts

```text
Review this Postgres schema and suggest indexes for the most common query patterns.
```

```text
This query is slow under load. Use EXPLAIN ANALYZE and recommend the smallest safe optimization.
```

```text
We're upgrading from PostgreSQL 15 to 17 with minimal downtime. Walk me through the logical replication approach and the pre/post checklist.
```

```text
Design RLS policies so each tenant only sees its own rows, and explain the caveats around table owners and superusers.
```

## Install

```sh
./install.sh --target claude --skill postgres-best-practices /path/to/project
```

`--target` defaults to `all` (install for every supported agent); use `--target agents|claude|openclaude|zcode` to select a single agent, and `--skill <name>` to install only this skill.

## Source and license

The guidance is authored for this repository and describes the PostgreSQL project's own documented behavior; no upstream skill, project URL, or bundled `LICENSE` file accompanies this skill.