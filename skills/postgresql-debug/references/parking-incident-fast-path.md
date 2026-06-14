# Parking Incident Fast Path

Use this reference when debugging parking incidents that cross a platform
database and a middleware or barrier database.

Replace placeholders such as `<PLATE_NO>`, `<ORDER_NO>`, `<ORDER_ID>`,
`<START_TS>`, and `<END_TS>` before running the queries.

Typical symptoms:

- User says payment succeeded but the barrier did not open
- Exit device returns `ORDER_NOT_EXIST`
- Platform shows the vehicle left, but middleware still shows it parked
- Plate, order, or device state looks inconsistent across services

## High-yield sequence

1. Confirm both connections and the effective schemas.
   If the DB endpoint is already reachable from the current machine, do this
   directly against PostgreSQL first instead of starting from JumpServer.
2. Write down the exact business keys and absolute timestamps before branching
   into queries.
3. Resolve the real physical tables before querying business data.
4. Query the platform order state by `plate_no` and `order_no`.
5. Query platform payment rows and barrier logs around the incident window.
6. Query platform audit logs for manual away, price-change request, and
   approval.
7. Query middleware `public.order_list` for the same `plate_no` or
   `barrier_order`.
8. Compare timestamps and final states, then explain the incident in terms of
   facts.

## Stable keys and what they mean

Prefer these keys in this order:

- `order_no`: platform-side parking order number
- `out_order_no`: external order number passed across service boundaries
- `barrier_order`: middleware or device-side order number when present
- `parking_id`: middleware parking session identifier
- `message_id`: one request or callback trace identifier, not the parking order
- `device_no`: physical device identifier
- `plate_no`: useful for entry, but less stable than order identifiers because
  OCR correction and manual plate changes can happen later

Practical rule:

- Start with `plate_no` only to find candidate rows.
- Once you have `order_no`, `out_order_no`, `barrier_order`, or `parking_id`,
  switch to those keys immediately.

Record the incident window with absolute timestamps such as
`2026-04-07T09:30:00+08:00`. Do not rely on "just now", "today", or UI-local
relative times.

## Schema and table resolution

Effective schemas:

```sql
select current_schemas(true) as schemas;
```

Resolve exact physical tables for a logical name:

```sql
select
  n.nspname as schema_name,
  c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r'
  and c.relname in ('barrier_log', 'order_list', 'trade_list_internal', 'parking_lot')
order by n.nspname, c.relname;
```

Find split tables by prefix:

```sql
select
  n.nspname as schema_name,
  c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r'
  and (
    c.relname like 'order_list%'
    or c.relname like 'trade_list_internal%'
    or c.relname like 'parking_lot%'
    or c.relname like 'device_list%'
  )
order by c.relname;
```

## Platform order state

Common pattern:

- active parking rows live in `ipms.order_list_parking`
- finished rows live in `ipms.order_list_away`
- middleware keeps one `public.order_list` with `parking_status`

Query the platform order by plate:

```sql
select
  o.id,
  o.order_no,
  o.out_order_no,
  o.plate_no,
  o.parking_status,
  o.pay_status,
  o.price,
  o.paid_fee,
  o.lastest_pay_time,
  o.parking_time,
  o.away_time,
  o.updated_at,
  o.parking_lot_id
from ipms.order_list_away o
where o.plate_no = '<PLATE_NO>'
order by o.updated_at desc
limit 10;
```

If nothing is returned, check the active table:

```sql
select
  o.id,
  o.order_no,
  o.out_order_no,
  o.plate_no,
  o.parking_status,
  o.pay_status,
  o.price,
  o.paid_fee,
  o.lastest_pay_time,
  o.parking_time,
  o.away_time,
  o.updated_at,
  o.parking_lot_id
from ipms.order_list_parking o
where o.plate_no = '<PLATE_NO>'
order by o.updated_at desc
limit 10;
```

## Platform payment and barrier logs

Important directionality:

- price query and exit pricing checks answer "how much should be paid now"
- payment upload endpoints carry payment evidence from middleware or vendor
  integrations into the platform
- `payNotify` is the platform pushing payment-confirmed state toward the
  barrier or downstream device path

Do not treat `payNotify` as proof that the platform received the original
payment callback. For incident triage, upstream payment evidence must come from
payment tables or upload-trade style logs first.

Payment rows often live in split tables:

```sql
select 'success' as tbl, rela_no, out_trade_no, trade_type, method, status, real_fee, receive_time, updated_at
from ipms.trade_list_internal_success
where rela_no = '<ORDER_NO>'
union all
select 'waiting' as tbl, rela_no, out_trade_no, trade_type, method, status, real_fee, receive_time, updated_at
from ipms.trade_list_internal_waiting
where rela_no = '<ORDER_NO>'
union all
select 'fail' as tbl, rela_no, out_trade_no, trade_type, method, status, real_fee, receive_time, updated_at
from ipms.trade_list_internal_fail
where rela_no = '<ORDER_NO>'
order by updated_at desc;
```

Barrier logs around the incident window:

```sql
select
  id,
  created_at,
  updated_at,
  status,
  process_status,
  error_code,
  order_no,
  plate_no,
  device_id,
  port_id,
  left(coalesce(data::text, ''), 300) as data
from ipms.barrier_log
where plate_no = '<PLATE_NO>'
  and updated_at between '<START_TS>' and '<END_TS>'
order by updated_at asc;
```

High-signal statuses:

- `before_away`: device asked for the current payable amount
- `away`: device reported the vehicle leaving
- `upload_trade`: middleware reported a payment serial
- `pay_notify`: platform pushed payment confirmation to the barrier
- `update_price`: price refresh or reconciliation event

Practical rule:

- If there is no payment row and no upload-trade style record, do not describe
  the incident as "paid but not opened". Describe it as "the platform did not
  receive a successful payment event".

## Audit and manual-operation logs

Check these early. They can explain the whole incident faster than code review.

```sql
select
  id,
  created_at,
  operator,
  type,
  target_id,
  content
from ipms.base_log
where target_id = '<ORDER_ID>'
   or content like '%<ORDER_NO>%'
   or content like '%<PLATE_NO>%'
order by created_at asc;
```

Look for:

- `manual_away`
- `change_order_price_request`
- `change_order_price_audit`
- plate correction logs

These records are often the fastest explanation for a later
`ORDER_NOT_EXIST`, `ORDER_AWAY`, or zero-amount completion.

## Middleware state

Middleware often keeps one raw order row:

```sql
select
  id,
  order_no,
  barrier_order,
  plate_no,
  parking_status,
  price,
  paid_fee,
  pay_time,
  out_pay_order,
  out_pay_time,
  parking_time,
  away_time,
  parking_id,
  parking_device,
  away_device,
  updated_at
from public.order_list
where plate_no = '<PLATE_NO>'
order by updated_at desc
limit 20;
```

## Device and port labels

```sql
select 'device' as kind, id, name, device_no, type, status
from ipms.device_list_true
where id in ('device-id-1', 'device-id-2')
union all
select 'device' as kind, id, name, device_no, type, status
from ipms.device_list_false
where id in ('device-id-1', 'device-id-2')
union all
select 'port' as kind, id, name, null::text as device_no, type, status
from ipms.port
where id in ('port-id-1', 'port-id-2');
```

## Test and debug endpoints

Treat Postman collections, manuals, and local test endpoints as helpful but not
authoritative.

Before depending on a debug endpoint during incident triage:

- verify the route exists in the current codebase or deployment
- verify the endpoint direction, for example whether it simulates downstream
  open-gate behavior or upstream payment upload
- prefer database facts over test-endpoint output when they disagree

## Interpretation patterns

- `before_away` shows a payable amount, but there is no payment trade row and
  no `upload_trade` or `pay_notify` record:
  the platform did not receive a successful payment event.
- Later `away` returns `ORDER_NOT_EXIST`, and audit logs show `manual_away` or
  a price-change approval:
  the order was manually ended before the device retried.
- Platform order is `away/completed`, but middleware `public.order_list` still
  says `parking` or unpaid:
  there is state drift or an async sync gap between services.
- Platform and middleware share the same backend server through different
  database names:
  treat it as a cross-database investigation, not a single-schema query.
