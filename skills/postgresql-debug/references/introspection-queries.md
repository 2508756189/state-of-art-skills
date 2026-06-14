# PostgreSQL Introspection Queries

Replace schema, table, and column placeholders before running these queries.
Prefer schema-qualified names such as `public.orders`.

## Table of Contents

- Session and server basics
- Schema and physical-table resolution
- Schemas, tables, and views
- Columns and definitions
- Constraints and indexes
- Row counts, size, and freshness
- Record sampling
- Metadata search
- Activity and blocking
- Execution plans

## Session and server basics

```sql
select
  current_database() as database_name,
  current_user as session_user,
  version() as server_version,
  now() as observed_at;
```

```sql
show search_path;
```

```sql
select current_schemas(true) as effective_schemas;
```

## Schema and physical-table resolution

Resolve the exact physical relation when the expected app table is missing or
the database uses split tables:

```sql
select
  n.nspname as schema_name,
  c.relname as table_name,
  c.relkind
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relname in ('orders', 'order_list', 'trade_list_internal', 'barrier_log')
order by n.nspname, c.relname;
```

Find related physical tables by prefix:

```sql
select
  n.nspname as schema_name,
  c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r'
  and c.relname ilike 'order_list%'
order by c.relname;
```

## Schemas, tables, and views

```sql
select schema_name
from information_schema.schemata
where schema_name not in ('pg_catalog', 'information_schema')
order by schema_name;
```

```sql
select
  table_schema,
  table_name,
  table_type
from information_schema.tables
where table_schema not in ('pg_catalog', 'information_schema')
order by table_schema, table_name;
```

```sql
select
  schemaname,
  viewname
from pg_catalog.pg_views
where schemaname not in ('pg_catalog', 'information_schema')
order by schemaname, viewname;
```

## Columns and definitions

```sql
select
  ordinal_position,
  column_name,
  data_type,
  is_nullable,
  column_default
from information_schema.columns
where table_schema = 'public'
  and table_name = 'orders'
order by ordinal_position;
```

```sql
select pg_get_viewdef('public.active_orders'::regclass, true);
```

## Constraints and indexes

Primary, unique, foreign-key, and check constraints:

```sql
select
  tc.constraint_name,
  tc.constraint_type,
  kcu.column_name,
  ccu.table_schema as foreign_table_schema,
  ccu.table_name as foreign_table_name,
  ccu.column_name as foreign_column_name
from information_schema.table_constraints tc
left join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name
 and tc.table_schema = kcu.table_schema
left join information_schema.constraint_column_usage ccu
  on tc.constraint_name = ccu.constraint_name
 and tc.table_schema = ccu.table_schema
where tc.table_schema = 'public'
  and tc.table_name = 'orders'
order by tc.constraint_type, tc.constraint_name, kcu.ordinal_position;
```

Indexes:

```sql
select
  schemaname,
  tablename,
  indexname,
  indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'orders'
order by indexname;
```

## Row counts, size, and freshness

Estimated row counts:

```sql
select
  n.nspname as schema_name,
  c.relname as table_name,
  c.reltuples::bigint as estimated_rows
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r'
  and n.nspname not in ('pg_catalog', 'information_schema')
order by estimated_rows desc nulls last;
```

Actual count for one table:

```sql
select count(*) as actual_rows
from public.orders;
```

Table and index size:

```sql
select
  pg_size_pretty(pg_relation_size('public.orders')) as table_size,
  pg_size_pretty(pg_indexes_size('public.orders')) as index_size,
  pg_size_pretty(pg_total_relation_size('public.orders')) as total_size;
```

Statistics freshness and write patterns:

```sql
select
  schemaname,
  relname as table_name,
  n_live_tup,
  n_dead_tup,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
from pg_stat_user_tables
where schemaname = 'public'
  and relname = 'orders';
```

## Record sampling

Newest rows by timestamp:

```sql
select *
from public.orders
order by created_at desc
limit 20;
```

Random sample on a large table:

```sql
select *
from public.orders
tablesample system (1)
limit 20;
```

Distinct values for a suspicious status column:

```sql
select status, count(*)
from public.orders
group by status
order by count(*) desc, status;
```

## Metadata search

Find tables by name:

```sql
select
  table_schema,
  table_name
from information_schema.tables
where table_schema not in ('pg_catalog', 'information_schema')
  and table_name ilike '%order%'
order by table_schema, table_name;
```

Find columns by name:

```sql
select
  table_schema,
  table_name,
  column_name,
  data_type
from information_schema.columns
where table_schema not in ('pg_catalog', 'information_schema')
  and column_name ilike '%user%'
order by table_schema, table_name, ordinal_position;
```

## Activity and blocking

Current active sessions:

```sql
select
  pid,
  usename,
  application_name,
  client_addr,
  state,
  wait_event_type,
  wait_event,
  now() - query_start as running_for,
  query
from pg_stat_activity
where datname = current_database()
order by query_start nulls last;
```

Blocked and blocking sessions:

```sql
select
  blocked.pid as blocked_pid,
  blocked.query as blocked_query,
  blocking.pid as blocking_pid,
  blocking.query as blocking_query
from pg_stat_activity blocked
join pg_stat_activity blocking
  on blocking.pid = any(pg_blocking_pids(blocked.pid));
```

## Execution plans

Planner-only view:

```sql
explain (verbose, costs, settings)
select *
from public.orders
where user_id = 42
order by created_at desc
limit 20;
```

Measured execution on a safe read-only query:

```sql
explain (analyze, buffers, verbose)
select *
from public.orders
where user_id = 42
order by created_at desc
limit 20;
```

`EXPLAIN ANALYZE` actually executes the query. Use it only when the statement is
safe to run and bounded.
