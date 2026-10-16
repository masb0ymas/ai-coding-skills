# gofi skills — audit findings

Scope: the gofi skills, now the `gofi` Claude Code plugin at `plugins/gofi/`
(`skills/{scaffold,layers,deploy,maintenance}`). Audited 2026-10-16.

## What was verified

- `scaffold.py` → fresh project: `go build`, `go vet`, `go test ./...` all pass; no stray `gofi` identifiers left.
- `new_resource.py` with every field type (`string text int float bool uuid time`, `required`, `max=`, `ref=`, `unique`) and all three `--access` modes, plus `--no-soft-delete`: everything builds, vets, and passes tests; `audit_layers.py` reports 0 errors and 0 warnings.
- `apply_deploy.py` in `api`, `embedded`, and `separate` modes with `--compose`: builds and tests pass, and a second run is a no-op (idempotent).
- `health.sh --quick` and `check_env_sync.py` on the patched project: all checks PASS.

- 2026-10-16, after the fixes: `docker compose up --build --wait` in all three modes (PG18 migrations, `api`
  healthy) with probes for `/health`, `/v1/*` JSON 404, `/static/*`, SPA fallback and immutable `/assets/*` where
  relevant, the unpublished API port in `separate`, and an `X-Forwarded-For` spoofing check.

**Not verified:** the `cmd/api` integration test (`TEST_DB_DSN`).

---

## Issues

### 1. `gofi-skills/` is a byte-identical copy of the other four skills — High (maintenance) — RESOLVED

**Resolved 2026-10-16:** the duplicate was removed and the four skills now live once, in the
`gofi` plugin at `plugins/gofi/`. Claude Code loads them as `/gofi:scaffold`, `/gofi:layers`,
`/gofi:deploy`, and `/gofi:maintenance`, and the plugin is listed in `.claude-plugin/marketplace.json` and the root
`README.md`. The original finding is kept below for reference.

`skills/gofi-skills/{gofi-scaffold,gofi-layers,gofi-deploy,gofi-maintenance}` is a full
duplicate: 103 files, about 8.2k lines, 592 KB. Consequences:
- Every edit has to be made twice, and the copies drift silently. The English translation already needed a manual re-sync.
- `install.sh` (default `all`) copies `skills/.` into every agent folder, so each project gets
  `.claude/skills/gofi-skills/…` (×4 agents). Because it has no `SKILL.md` at its root, none of the nested skills load from there. It is dead weight.
- `gofi-skills/README.md` says to "upload each `gofi-*.zip`", but no zip files exist.
- It breaks the repo's own rules in the root `README.md` ("Adding or updating a skill" steps 2–4): there is no
  `SKILL.md`, and none of the four gofi skills has a `docs/<skill>/README.md` or a row in "Available skills".

**Fix:** delete `skills/gofi-skills/`. Move its README content to `docs/gofi/README.md` and add
the four skills to the skills table in the root `README.md`, matching how `authula` and `typeorm` are documented.

### 2. The compose file trusts every private network as a proxy and also publishes the API port — Medium (security) — RESOLVED

**Resolved 2026-10-16:** `TRUSTED_PROXIES` defaults to empty. With `--mode separate --compose`, the network is pinned to
`COMPOSE_SUBNET` (default `172.30.250.0/24`), the API trusts only that subnet, the API port is `expose`d instead of
published, and `web` is no longer behind a profile (it is the only way in).
Live testing found a second hole: nginx used `$proxy_add_x_forwarded_for`, which keeps the client's own header in
front, and Fiber reads the first valid entry, so a spoofed `X-Forwarded-For` still picked its own rate-limit bucket
(0 of 125 requests limited). nginx now sends `X-Forwarded-For $remote_addr`. After the fix: spoofed requests hit 429
after 120, and a second client still gets 200, so the API sees real client IPs rather than nginx's.

`plugins/gofi/skills/deploy/assets/compose/docker-compose.yml` defaults
`TRUSTED_PROXIES=172.16.0.0/12,192.168.0.0/16,10.0.0.0/8` in **all** modes and publishes `api` on
`:8080`. The upstream default is empty on purpose (see `cmd/api/server.go`, `EnableIPValidation`).
Any client whose source IP falls in a private range can then set `X-Forwarded-For` to whatever it wants,
and every value gets its own rate-limit bucket. That covers LAN or VPC peers, and Docker Desktop/OrbStack port-forwarding, where traffic arrives from the gateway IP. In `api` and `embedded` modes there is no proxy at all, yet the comment still says "so the nginx in front is believed".

**Fix:** default `TRUSTED_PROXIES` to empty. Have `apply_deploy.py --mode separate` set it to the compose
network subnet only, by pinning `networks.default.ipam.config.subnet` and using that CIDR. In
`separate` mode, also stop publishing the API port (`expose` instead of `ports`).

### 3. `--access auth` / `--access private` give every signed-in user access to every row — Medium (security, docs) — RESOLVED

**Resolved 2026-10-16:** `new_resource.py` prints the warning for `auth`/`private`, and its `--help` and `layers/SKILL.md` say rows are not owner-scoped and point to `patterns.md` §4.

`new_resource.py` gates the routes with `m.Authorization` only. Handlers and repositories have
no owner filter, so any logged-in user can read, update, and delete any other user's rows. The name
`private` reads as "per-user data", which makes an IDOR easy to ship by accident. The manual fix exists
(`references/patterns.md` §4), but neither the generator nor `SKILL.md` points to it at the moment of choice.

**Fix:** in `new_resource.py`, print a warning for `auth` and `private` ("rows are shared by all
signed-in users; for per-user data follow patterns.md §4"). In `plugins/gofi/skills/layers/SKILL.md`, reword
`private` to "every route requires login (rows are not owner-scoped)".

### 4. Three copies of the import rules, and they already disagree — Low (docs) — RESOLVED

**Resolved 2026-10-16:** the `structure.md` column now matches `ALLOWED`, and both it and `audit_layers.py` name `ALLOWED` as the source of truth.

The allowed-import rules live in `plugins/gofi/skills/layers/scripts/audit_layers.py` (`ALLOWED`),
`plugins/gofi/skills/layers/SKILL.md` (contract table), and `plugins/gofi/skills/scaffold/references/structure.md` ("May import").
They differ:
- `internal/dtos`: `structure.md` lists `lib/validator, lib/apperr`; the audit also allows `lib/constant`.
- `internal/middlewares`: `structure.md` lists `app, config, lib*`; the audit also allows `internal/dtos`.

**Fix:** treat `ALLOWED` as the single source of truth. Drop the "May import" column from
`structure.md` and point readers to `audit_layers.py`, or bring the column in line with it.

### 5. `apply_deploy.py` leaves `Dockerfile.bak` in the repo and the build context — Low — RESOLVED

**Resolved 2026-10-16:** `*.bak` is added to `.dockerignore`, and the report says to delete the backup once reviewed.

`.bak` files are not added to `.gitignore` or `.dockerignore`, so they are easy to commit and are sent
to every `docker build`. **Fix:** append `*.bak` to `.dockerignore`, or say in the report that git history already keeps the old version and skip the backup.

### 6. `new_resource.py` crashes on a non-numbered `.sql` file in `migrations/` — Low — RESOLVED

**Resolved 2026-10-16:** uses the single pass below; generating with a stray `migrations/README.sql` works.

`new_resource.py:727` calls `re.match(...).group(1)` on every `*.sql` without a `None` check, which raises
`AttributeError` (line 726 filters correctly; line 727 does not). **Fix:** compute both values in one pass:

```python
nums = [m.group(1) for p in mig_dir.glob("*.sql") if (m := re.match(r"^(\d+)_", p.name))]
seq = str(max(map(int, nums), default=0) + 1).zfill(max(map(len, nums), default=6))
```

### 7. The `time` field validator accepts timestamps without a zone — Low — RESOLVED

**Resolved 2026-10-16:** `TIME_RE` now requires a zone (`Z` or `±hh:mm`), with optional fractional seconds.

`TIME_RE = ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` passes `2026-01-02T15:04:05`, but binding into
`time.Time` needs RFC 3339 with a zone. The client gets a generic `400 invalid JSON body` instead of a
422 that names the field. **Fix:** end the pattern with `(\.\d+)?(Z|[+-]\d{2}:\d{2})$`.

### 8. `separate` mode: nginx does not proxy the API's `/static/` — Low — RESOLVED

**Resolved 2026-10-16:** `default.conf.template` proxies `/static/` to the API.

The API serves `./public` (for example `/static/images/golang.jpg`), but `default.conf.template` only proxies
`/v1/` and `/health`, so those files return the SPA shell. **Fix:** add a `location /static/` proxy
block, or document that `public/` is not reachable in `separate` mode.

---

## Simplifications (over-engineering) — all applied 2026-10-16

| Tag | Cut | Replacement | Where |
|---|---|---|---|
| ~~delete~~ | ~~the whole `gofi-skills/` duplicate tree (−8.2k lines)~~ done: moved to the `gofi` plugin | — | `plugins/gofi/` |
| ~~delete~~ | ~~README comparison in the env check: 10 INFO lines on a freshly scaffolded project and it never fails~~ | ~~nothing; `.env.example` is the enforced contract~~ | `plugins/gofi/skills/maintenance/scripts/check_env_sync.py` (`readme`, `missing_readme`) (done) |
| ~~yagni~~ | ~~`write(..., backup=True)` parameter and its `else` branch; no caller ever passes `False`~~ | ~~always back up~~ | `plugins/gofi/skills/deploy/scripts/apply_deploy.py:41` (done) |
| ~~yagni~~ | ~~`--no-dockerfile` flag: undocumented in `SKILL.md`/`deploy.md` and never mentioned~~ | ~~drop it; the `.bak` already protects a custom Dockerfile~~ | `apply_deploy.py:179` (done) |
| ~~shrink~~ | ~~`"lib/*"` special case in `allowed()`~~ | ~~`target == rule or target.startswith(rule + "/")`, then remove `"lib/*"` from `ALLOWED`~~ | `plugins/gofi/skills/layers/scripts/audit_layers.py:66` (done) |
| ~~shrink~~ | ~~`f.ref or f.searchable and f.kind == "string"`~~ | ~~`f.ref or f.kind == "string"`~~ | `new_resource.py:177` (done) |
| ~~shrink~~ | ~~two regex passes over `migrations/*.sql`~~ | ~~the single pass shown in issue 6~~ | `new_resource.py:726-727` (done) |
| ~~shrink~~ | ~~`p.name in ("factory.go",)`~~ | ~~`p.name == "factory.go"`~~ | `audit_layers.py:140` (done) |
| ~~shrink~~ | ~~`gofmt -l $(find . -name '*.go' -not -path './vendor/*')`~~ | ~~`gofmt -l .`~~ | `plugins/gofi/skills/maintenance/assets/ci.yml` (done) |
| ~~delete~~ | ~~empty `templates/` folder (only a `.gitignore`; no Go code reads it)~~ | ~~nothing, or filter it in `scaffold.py` so the upstream snapshot stays untouched~~ | `plugins/gofi/skills/scaffold/template/templates/` (done) |

Not cut on purpose: the duplicated Node build stage in `Dockerfile.fullstack` / `Dockerfile.web`
(each is copied into user projects on its own) and `REPO_SPECIFIC` in `scaffold.py` (it does nothing for the
bundled snapshot but is needed for `--source github`).
