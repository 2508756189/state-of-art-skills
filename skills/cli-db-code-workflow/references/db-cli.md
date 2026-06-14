# Database CLI Reference

## Tool Choice

- Prefer `psql` for PostgreSQL inspection and small data fixes.
- Use `information_schema` before assuming column names.
- Use read-only `select` queries first; only run `insert`, `update`, or `delete` after the user explicitly asks for a DB write.
- Do not put database hosts, ports, database names, usernames, or passwords in skill files.
- Require the user to provide connection details for the current task instead of guessing or using a remembered project default.

## PowerShell Connection Pattern

Set `PGPASSWORD` only for the command window scope, then clear it:

```powershell
$env:PGPASSWORD = '<password-from-user>'
psql -h <host> -p <port> -U <user> -d <database> -c "select now();"
Remove-Item Env:\PGPASSWORD
```

For multi-line SQL, use a PowerShell here-string:

```powershell
$sql = @"
select table_schema, table_name
from information_schema.tables
where table_schema = '<schema_name>'
order by table_name
limit 20;
"@

$env:PGPASSWORD = '<password-from-user>'
psql -h <host> -p <port> -U <user> -d <database> -c $sql
Remove-Item Env:\PGPASSWORD
```

## Required Connection Inputs

Before live DB access, ensure the user has provided:

- `host`
- `port`
- `database`
- `username`
- `password`
- target schema or table if the task depends on a specific business schema

If any required value is missing, ask for it. Do not infer from previous projects or skill files.

## Discovery Queries

Find schemas:

```sql
select schema_name
from information_schema.schemata
order by schema_name;
```

Find tables:

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = '<schema_name>'
order by table_name;
```

Find columns:

```sql
select column_name, data_type
from information_schema.columns
where table_schema = '<schema_name>'
  and table_name = '<table_name>'
order by ordinal_position;
```

Check request-log tables by date:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name like 'request_log_%'
order by table_name desc
limit 10;
```

## Safe Query Habits

- Add `limit` when inspecting large tables.
- Use exact identifiers such as `order_no`, `id`, `pile_no`, `mobile`, or `card_no`.
- For updates, run a `select` with the same `where` clause first.
- For writes, prefer wrapping related changes in `begin; ... commit;` when using an interactive session.
- After a write, immediately verify with a `select`.

## Network Failure Interpretation

- `Permission denied` from CLI can be an execution/network sandbox issue, not necessarily a database credential problem.
- If GUI tools such as Navicat connect but CLI fails, check whether the current execution environment has network access.
- Authentication errors usually look different from network permission or connection timeout errors.
