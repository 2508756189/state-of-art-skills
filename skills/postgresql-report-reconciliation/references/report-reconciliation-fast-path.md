# Report Reconciliation Fast Path

Use this reference when a user reports a mismatch such as:

- "net amount and system flow differ by 34"
- "the daily export does not match the ledger"
- "where does this income column come from"
- "check production and prove which side is wrong"

## Goal

Move from screenshot-level suspicion to a defensible conclusion with:

1. direct order-level proof when possible
2. statistics-table proof when the report is precomputed
3. code or logic-resource proof for how the report column is assembled
4. a clear statement of which parts are proved and which are inferred

## Workflow

1. Lock the report contract.
   Record the exact column names, formula, grouping grain, filters, and date
   window. If the report is grouped by date, owner, area, or parking lot, write
   that down before querying.
2. Confirm the live environment.
   Verify database, schema, and tenant binding first. Do not assume the report
   comes from the local codebase's default environment.
3. Build a source map for each column.
   For every report column, classify the likely source as one of:
   - external bank or channel file
   - raw transactions or refunds
   - derived statistics table
   - logic resource or function
   - spreadsheet formula
4. If an external payment file is present, prove that layer first.
   Recompute its positive rows, negative rows, fees if available, and net
   amount. Then match merchant order numbers and refund numbers to raw system
   rows before blaming the business report.
5. Prove easy columns from raw tables first.
   Start with grouped totals by day, `trade_type`, and `method`.
6. Separate real, virtual, and allowance amounts.
   Keep `actual_received`, `real_fee`, `virtual_fee`, and
   `method_allowance` distinct all the way through the analysis.
7. Only then inspect statistics jobs and report SQL.
   When the raw totals differ from a report column, inspect the precompute path
   for splits, rounding, or correction logic.
8. Close with evidence levels.
   Mark each conclusion as:
   - external-file proof
   - direct proof
   - statistics-table proof
   - code-path proof
   - inference from matching totals

## Querying Rules

- Prefer one focused query per check. The helper is more reliable with single
  `SELECT` statements than with long multi-statement batches.
- Use explicit timestamps.
- Use schema-qualified names once the real schema is known.
- If connecting as a superuser or shared account, verify `current_schemas(true)`
  and use `set search_path = app_schema, public` or fully qualified table
  names. Do not assume unqualified names resolve to the business schema.
- For bank-day reconciliation, match the external order list directly. A
  payment gateway's settlement day and the system's `receive_time` timezone can
  differ.
- Add `count(*)` checks for negative claims such as "no refund row exists".
- When a result is empty, verify the date column and time column used in the
  table before concluding the data is missing.

## Templates

### 1. Confirm connection and schema

```sql
select current_database(), current_user, current_schemas(true), now();
```

### 2. Group raw trades by day, trade type, and method

```sql
select
  trade_type,
  method,
  count(*) as cnt,
  sum(actual_received) as actual_received,
  sum(real_fee) as real_fee,
  sum(virtual_fee) as virtual_fee,
  sum(coalesce(method_allowance, 0)) as method_allowance
from app_schema.trade_list_internal
where status = 'success'
  and data_owner_id = '<owner-id>'
  and receive_time >= timestamp '<start>'
  and receive_time < timestamp '<end>'
group by trade_type, method
order by trade_type, method;
```

### 3. Group refunds with the same dimensions

```sql
select
  trade_type,
  method,
  count(*) as cnt,
  sum(refund_real_fee) as refund_real_fee,
  sum(refund_virtual_fee) as refund_virtual_fee,
  sum(coalesce(refund_method_allowance, 0)) as refund_method_allowance
from app_schema.refund_list
where status = 'success'
  and data_owner_id = '<owner-id>'
  and commit_time >= timestamp '<start>'
  and commit_time < timestamp '<end>'
group by trade_type, method
order by trade_type, method;
```

### 4. Drill into the exact orders behind one suspect column

```sql
select
  to_char(receive_time, 'YYYY-MM-DD HH24:MI:SS') as receive_time,
  out_trade_no,
  rela_no,
  actual_received,
  real_fee,
  virtual_fee,
  coalesce(method_allowance, 0) as method_allowance,
  options::text
from app_schema.trade_list_internal
where status = 'success'
  and trade_type = '<trade-type>'
  and method = '<method>'
  and data_owner_id = '<owner-id>'
  and receive_time >= timestamp '<start>'
  and receive_time < timestamp '<end>'
order by receive_time;
```

### 5. Prove that no matching refund exists

```sql
select
  count(*) as refund_cnt,
  coalesce(sum(refund_real_fee), 0) as refund_real_fee,
  coalesce(sum(refund_virtual_fee), 0) as refund_virtual_fee
from app_schema.refund_list
where status = 'success'
  and trade_type = '<trade-type>'
  and method = '<method>'
  and data_owner_id = '<owner-id>'
  and commit_time >= timestamp '<start>'
  and commit_time < timestamp '<end>';
```

### 6. Sanity-check a precomputed statistics table

Use this when you suspect the report column is coming from a statistics table
instead of raw trades.

```sql
select
  sum(income) as income,
  sum(refund) as refund,
  sum(balance) as balance,
  sum(income_wallet_real) as income_wallet_real,
  sum(income_wallet_virtual) as income_wallet_virtual,
  sum(refund_wallet_real) as refund_wallet_real,
  sum(refund_wallet_virtual) as refund_wallet_virtual
from app_schema.statistics_time_card
where sta_date = date '<date>';
```

If the table also stores channel columns, compare `income` against the sum of
channel incomes. A mismatch often signals a correction step that updated some
channel columns but not `income` or `balance`.

### 7. Match a payment-channel file to raw system rows

Use this after parsing a bank or payment CSV into two lists: successful payment
order numbers and refund numbers. It proves whether the external file itself is
missing or mismatched before investigating report logic.

```sql
with ext_pay(order_no, amount) as (
  values
    ('<merchant-pay-order-no>', numeric '<amount>')
),
pay_match as (
  select
    e.order_no,
    e.amount as external_amount,
    o.trade_no,
    o.trade_type,
    o.pay_type,
    o.method,
    o.status,
    o.actual_received,
    o.real_fee,
    o.receive_time
  from ext_pay e
  left join app_schema.trade_list_out o on o.trade_no = e.order_no
)
select *
from pay_match
where trade_no is null
   or status <> 'success'
   or actual_received <> external_amount
order by order_no;
```

Run the same shape for refunds:

```sql
with ext_refund(refund_no, amount) as (
  values
    ('<merchant-refund-no>', numeric '<amount>')
)
select
  e.refund_no,
  e.amount as external_amount,
  r.refund_no as matched_refund_no,
  r.trade_type,
  r.method,
  r.status,
  r.refund_real_fee,
  r.commit_time
from ext_refund e
left join app_schema.refund_list r on r.refund_no = e.refund_no
where r.refund_no is null
   or r.status <> 'success'
   or r.refund_real_fee <> e.amount
order by e.refund_no;
```

If both mismatch queries return zero rows, the external payment file and raw
system payment/refund rows agree. Continue at the business report or
operational order layer.

### 8. Classify externally matched payments by business type

```sql
with ext_pay(order_no, amount) as (
  values
    ('<merchant-pay-order-no>', numeric '<amount>')
)
select
  o.trade_type,
  o.pay_type,
  o.method,
  count(*) as cnt,
  sum(o.actual_received) as actual_received,
  sum(o.real_fee) as real_fee
from ext_pay e
join app_schema.trade_list_out o on o.trade_no = e.order_no
where o.status = 'success'
group by o.trade_type, o.pay_type, o.method
order by o.trade_type, o.pay_type, o.method;
```

This is the fastest way to isolate a residual such as "charging income is 10.00
higher in the bank file than in the charging report."

### 9. Verify whether statistics owner columns are usable

Some statistics tables keep `data_owner_id` or `data_owner_name` null and rely
on joins through `parking_lot`.

```sql
select
  coalesce(data_owner_id, '<null>') as data_owner_id,
  coalesce(data_owner_name, '<null>') as data_owner_name,
  count(*) as cnt
from app_schema.statistics_time_card
where sta_date = date '<date>'
group by data_owner_id, data_owner_name
order by cnt desc;
```

### 10. Search logic resources for report SQL

```sql
select
  name,
  left((config->>'logic')::text, 4000) as logic
from app_schema.base_resource
where type = 'logic'
  and (
    (config->>'logic') ilike '%statistics_time_card%' or
    (config->>'logic') ilike '%statistics_parking_card%' or
    (config->>'logic') ilike '%system flow%' or
    (config->>'logic') ilike '%net amount%' or
    (config->>'logic') ilike '%difference%'
  )
order by name;
```

If the exported report labels are not English, replace those three search
patterns with the exact labels copied from the sheet.

## Common Failure Modes

### Report uses a statistics table, not raw orders

A controller or export endpoint may read a precomputed table while the raw
tables still look correct.

### Statistics rows are allocated across dimensions

Card products are often split across every bound parking lot, area, or owner
dimension. The report value may be a filtered sum of many fractional rows, not
one obvious transaction.

### Rounding is repaired unevenly

Jobs may round every split row, then add the residual back to one row. If the
repair updates only selected channel columns, `income`, `balance`, and channel
totals can diverge.

### Null owner columns hide the real grouping path

If `data_owner_id` is null in the stats table, the report may be grouping by
`parking_lot -> data_owner_id` instead.

### Raw wallet flow and report income are different concepts

`actual_received`, `real_fee`, `virtual_fee`, and `balance_log.amount` are not
interchangeable. Always name which one you are using.

## Answering Carefully

Use wording like this when the evidence is mixed:

- "Direct order-level proof shows the raw virtual amount is 15.00."
- "The report's system flow matches that 15.00 raw-wallet reconstruction."
- "The final report SQL for the 49.00 column was not fully located, so its
  mapping is inferred from the statistics job and the residual value."

Do not overstate an inferred code path as if it were directly proved.
