---
name: "postgresql-debug"
description: "Connect to PostgreSQL safely for debugging and incident triage. Use when Codex needs to inspect schemas, sample records, compare environments, or trace live operational issues without modifying data."
---

# PostgreSQL Debug

Treat every session as read-only unless the user explicitly requests a write.
Prefer schema inspection, targeted sampling, and execution-plan analysis over
guessing.

## Start with connection discovery

Run the preflight helper first:

```powershell
powershell -ExecutionPolicy Bypass -File <path-to-skill>/scripts/pg-preflight.ps1
```

`pg-preflight.ps1` only checks the local route and available tooling. It does
not probe a remote host. If the user already gives a live host, port, database,
or user, skip directly to `invoke-psql.ps1` with `-DbHost`, `-Port`,
`-Database`, `-User`, and `-Password`.

## Direct DB vs bastion

Decide the access path before touching code or servers:

1. If the user already gives a reachable PostgreSQL endpoint such as a public
   IP or domain plus port, connect to that database directly first.
2. Do not introduce JumpServer or a bastion just to query data when the
   database endpoint is already reachable from the current machine.
3. Only switch to a bastion or service host when:
   - the database address is private and unreachable from the current machine;
   - the user explicitly asks to use the bastion path; or
   - you are no longer doing DB inspection and instead need app-host context
     such as process state, config files, local-only ports, or in-process
     service execution.
4. When the same public IP is both a DB endpoint and a service asset, treat
   these as separate paths:
   - DB facts: connect to PostgreSQL directly
   - service facts: use JumpServer or SSH to inspect the host

## Shortest path checklist

Use this exact order for live production triage:

1. User gave `host + port + db + user + password`:
   run `invoke-psql.ps1` directly.
2. First query:
   `select current_database(), current_user, inet_server_addr(), inet_server_port(), current_schemas(true), now();`
3. Confirm real schema and target tables.
4. Query the business rows you need.
5. Only after the DB facts are insufficient, switch to `production-ops` for
   app-host inspection.

Avoid these detours:

- do not SSH first just to rediscover a DB host the user already gave;
- do not read local config first when the live DB endpoint is already known;
- do not assume bastion access is required merely because the environment has a
  bastion.

Use these connection inputs in this order:

1. `DATABASE_URL` or `POSTGRES_URL`
2. `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
3. `docker exec <container> psql` when the PostgreSQL client is only available
   inside a running container
4. Project config and deployment files when the database is remote and the app
   is local. Check app config, `.env*`, Docker compose files, and ORM config
   before assuming the database is on the current machine.

If the user already gives a connection string, host, database, or container
name, use that directly instead of rediscovering it.

When running a query against an explicit host, use `-DbHost` instead of
`-Host` to avoid conflicting with PowerShell's built-in `$Host` variable.

If `psql` is unavailable but `node` and `npm` are installed, `invoke-psql.ps1`
now falls back to a temporary Node `pg` client automatically. Keep using the
same script; do not hand-roll an ad hoc client unless the fallback is blocked.

## Windows text encoding hygiene

On Windows, set UTF-8 before printing SQL results or reading Chinese text from
the shell. `invoke-psql.ps1` now does this itself, but use the same rule for ad
hoc shell reads:

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
chcp 65001 > $null
```

Practical rules:

- Prefer `Get-Content -Encoding utf8` for known UTF-8 files.
- If a legacy file still looks garbled, confirm whether it is actually GBK/936
  encoded before assuming the content itself is broken.
- When copying output into notes, prefer structured query output from
  `invoke-psql.ps1 -Expanded` over raw terminal screenshots.

## Default safety rules

- Use `scripts/invoke-psql.ps1` for ad hoc SQL execution.
- Let the helper keep queries in a read-only transaction by default.
- Do not run `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER`, `DROP`, or
  migration DDL unless the user explicitly asks for it.
- Avoid `SELECT *` on unknown large tables; first inspect columns and row count
  estimates, then fetch a small sample with `LIMIT`.
- Prefer exact schema-qualified names once the real schema is known. Do not
  assume `public`.
- Use `EXPLAIN (ANALYZE, BUFFERS)` only on safe read-only statements.
- When multiple services share a workflow, verify the real environment bindings
  first: parking lot, device, port, tenant, and schema names often drift from
  local assumptions.

## Fast path for live incident triage

Use this path when the user reports an operational issue such as "paid but the
barrier did not open", "order does not exist", "vehicle cannot exit", or "the
same plate looks different across services".

1. Connect to each database in the business path first. Confirm whether the
   public endpoint fronts one backend or separate platform and middleware
   databases.
2. Run `current_schemas(true)` immediately. Many production databases keep app
   tables outside `public`.
3. Resolve actual table names before querying records. Logical model names
   often land in split tables such as `order_list_away`,
   `trade_list_internal_success`, `parking_lot_true`, or a middleware
   `public.order_list`.
4. Pick one stable business key and one short time window. Prefer `plate_no`,
   `order_no`, `out_order_no`, `barrier_order`, `message_id`, `parking_id`, and
   `device_no`.
5. Use `plate_no` only to discover the candidate incident. Once an `order_no`,
   `out_order_no`, `barrier_order`, or `parking_id` is known, pivot to that
   identifier for the rest of the trace.
6. Pull the order state from both sides before reading code. Compare platform
   order tables, middleware order tables, payment rows, and barrier or device
   logs.
7. Separate upstream payment evidence from downstream open-gate pushes. Payment
   tables and upload-trade style logs prove whether the platform received a
   successful payment event; `payNotify` only proves what the platform tried to
   push afterward.
8. Check audit and manual-operation logs before calling it a runtime bug. A
   manual away, price change, or approval often explains later
   `ORDER_NOT_EXIST` responses.
9. Only conclude "payment succeeded but no open-gate" after proving the payment
   path exists in database facts. If there is no payment trade row and no pay
   callback log, say the platform did not receive the payment success.

## Core commands

Read-only query through local `psql` or container `psql`:

```powershell
powershell -ExecutionPolicy Bypass -File <path-to-skill>/scripts/invoke-psql.ps1 `
  -Sql "select current_database(), current_user, now();" `
  -Expanded
```

Run against a specific container:

```powershell
powershell -ExecutionPolicy Bypass -File <path-to-skill>/scripts/invoke-psql.ps1 `
  -Container postgres `
  -Database app_db `
  -User postgres `
  -Sql "select count(*) from public.users;"
```

Use a full connection string directly:

```powershell
powershell -ExecutionPolicy Bypass -File <path-to-skill>/scripts/invoke-psql.ps1 `
  -DatabaseUrl "postgresql://<user>:<password>@<host>:<port>/<database>" `
  -Sql "select * from public.users order by id desc limit 20;"
```

The same command works when `psql` is missing. The script will transparently
fall back to a temporary Node `pg` runtime if needed.

When the user already gave the connection details, this is the preferred shape:

```powershell
powershell -ExecutionPolicy Bypass -File <path-to-skill>/scripts/invoke-psql.ps1 `
  -DbHost "<host>" `
  -Port <port> `
  -Database "<db>" `
  -User "<user>" `
  -Password "<password>" `
  -Sql "select current_database(), current_user, inet_server_addr(), inet_server_port(), current_schemas(true), now();" `
  -Expanded
```

## Debug workflow

1. Confirm where you are connected: database, user, server version, search path.
2. Inventory schemas, tables, views, and row-count estimates.
3. Describe the target table: columns, defaults, nullability, primary keys,
   foreign keys, unique constraints, and indexes.
4. Sample a few rows with an explicit `ORDER BY` and `LIMIT`.
5. Compare actual filters and joins against constraints and indexes.
6. Use `EXPLAIN` or `EXPLAIN ANALYZE` when performance or planner choice is the
   problem.
7. Summarize findings in terms of facts from the database, not assumptions.

## Cross-service workflow

Use this when tracing one business event across a middleware database and a
platform database:

1. Verify the live configuration tables first. Confirm the real parking lot,
   device, and port bindings before chasing order data.
2. Pick stable business keys early: `plate_no`, `barrier_order`, `parking_id`,
   `order_no`, `message_id`, and `device_no`.
3. Resolve real table names before querying data. In production, platform
   tables may be partitioned or status-suffixed, while middleware may keep one
   flat `public` table.
4. Start from the narrowest log table, then fan out. For parking incidents this
   usually means platform `barrier_log`, platform payment tables, platform
   audit logs, then middleware `public.order_list`.
5. Compare timestamps across systems. This catches missing callbacks, delayed
   status updates, and mismatched environment routes.
6. Check manual-operation logs such as `base_log` or manager audit tables
   before concluding that a callback or device flow is broken.
7. Treat local simulator config as suspect until the platform bindings prove it
   matches production-like data.

## Practical lessons

- If the user gives a DB host and password directly, do not "helpfully" route
  through a bastion first. That changes the access path and wastes time.
- Do not assume the target database is local just because the codebase is
  local. In this session, the application ran locally while PostgreSQL lived on
  the server.
- Do not assume the target tables live in `public`, or that the logical model
  name is the physical table name. Production apps often use schemas such as
  `ipms` plus split tables like `order_list_away` or
  `trade_list_internal_success`.
- When debugging order closure bugs, query configuration tables before order
  tables. Missing parking-lot bindings and wrong device mappings look like code
  bugs until you check the data.
- Prefer precise `WHERE` clauses on business keys and recent timestamps over
  broad table scans.
- For read-path verification, correlate middleware logs and platform logs
  instead of trusting one side only.
- For "paid but did not open" incidents, prove the payment path first. No trade
  row plus no pay callback log usually means the platform never received a
  successful payment event.
- Use absolute timestamps and stable IDs in your notes and SQL. Relative times
  and plate-only tracing slow down live incident work.
- Audit logs can be the fastest explanation. A manual away or approved price
  change can make a later device retry return `ORDER_NOT_EXIST` even when the
  device appears to be using the same order number.
- Compare final state across services. If the platform order is `away` but the
  middleware order remains `parking`, you likely have a manual operation or
  asynchronous sync gap rather than a single-query bug.
- Treat Postman collections and test routes as aids, not authorities. Verify a
  debug endpoint exists in the current code or deployment before relying on it.

## References

Load [references/introspection-queries.md](references/introspection-queries.md)
when you need concrete SQL snippets for:

- schema and table discovery
- column, constraint, and index inspection
- table size and row-count estimates
- sample-row queries
- lock, activity, and execution-plan diagnostics

Load [references/parking-incident-fast-path.md](references/parking-incident-fast-path.md)
for a focused playbook when debugging parking incidents across platform and
middleware services, especially "paid but no barrier open", `ORDER_NOT_EXIST`,
or platform or middleware state drift.

## Interpreting results

- Treat `reltuples` and `pg_stat_*` counts as estimates unless you run an
  explicit `count(*)`.
- If a result depends on `search_path`, rerun it with a schema-qualified table
  name.
- If a query plan looks wrong, verify statistics freshness and index coverage
  before proposing code changes.
- If the database contains sensitive data, keep samples minimal and avoid
  copying full rows into the response unless the user needs them.
