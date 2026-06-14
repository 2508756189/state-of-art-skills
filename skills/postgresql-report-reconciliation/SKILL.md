---
name: "postgresql-report-reconciliation"
description: "Reconcile financial or operational reports against PostgreSQL data. Use when Codex needs to explain mismatches between report columns, raw trades, payment or bank CSVs, UnionPay/云闪付 allowance rows, statistics tables, exports, net amounts, system flow, charging or parking income, refunds, settlement figures, report rerun jobs, scheduleTest, or refund date buckets without modifying data."
---

# PostgreSQL Report Reconciliation

Treat every session as read-only unless the user explicitly requests a write.
This skill is for report mismatches, account checks, settlement discrepancies,
and export validation. It is not the default skill for barrier or device
incidents.

## When to use this skill

Use it for requests like:

- "why does the net amount differ from system flow"
- "connect to production and check why this export is off"
- "where does this report column come from"
- "prove which side is wrong: raw data or report"
- "which schedule job should I rerun for this report"
- "why did this refund fall into this month instead of that month"

If the problem is about payment success, barrier state, `ORDER_NOT_EXIST`, or a
device callback path, use `$postgresql-debug` instead.

## Query helper

Reuse the read-only PostgreSQL helper from `$postgresql-debug`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Administrator\.codex\skills\postgresql-debug\scripts\invoke-psql.ps1 `
  -DbHost <host> -Port <port> -Database <db> -User <user> -Password <password> `
  -Sql "select current_database(), current_user, current_schemas(true), now();" `
  -Expanded
```

If the user already gives a live host or port, skip discovery and connect
directly.

## Fast path

1. Lock the report contract first.
   Record the exact columns, formula, grouping grain, filters, and absolute
   date window. Do not reconcile a screenshot until those are explicit.
2. Split evidence into layers.
   Keep raw trades or refunds, derived statistics tables, logic resources or
   code, and spreadsheet formulas separate.
3. If a bank, channel, or payment CSV is present, parse it first.
   Rebuild the external file totals and match merchant order numbers or
   refund numbers to raw `trade_list_out` and `refund_list` rows before
   comparing business reports.
4. Gate refunds by external money-flow evidence when the task is account
   reconciliation.
   A system `refund_list.status = 'success'` proves only the application state.
   Do not use it to reduce a bank or channel balance unless the external file,
   channel settlement detail, or channel response identifiers prove a refund,
   reversal, or adjustment left the account. If the external export shows no
   refund/adjustment row and the channel result payload has no usable external
   refund number, keep the external gross amount and classify the gap as an
   externally unsettled or failed refund for reconciliation purposes.
5. Rebuild easy columns from raw transactions first.
   Group by `trade_type`, `method`, `data_owner_id`, and date before reading
   report SQL.
6. Keep `actual_received`, `real_fee`, `virtual_fee`, and
   `method_allowance` separate.
   Report mismatches often come from mixing total received with wallet real,
   wallet virtual, or channel allowance values.
   For UnionPay allowance also keep channel allowance refunds separate:
   a pure allowance refund can have `refund_real_fee = 0` and
   `refund_method_allowance > 0`, so cash-only refund filters can miss it.
   Still apply the external money-flow gate above before reducing an external
   bank/channel balance.
7. Use explicit negative checks.
   Run `count(*)` queries for missing refunds, missing trades, or empty
   dimensions instead of treating a blank result as proof.
8. If a report column still does not match raw trades, inspect the scheduled
   jobs, DB functions, or logic resources that precompute the statistics.
   Compare statistics-table total columns against the sum of their channel
   columns before assuming the raw trades are wrong.
   When the user asks what to rerun, trace page or controller -> statistics
   table -> schedule job -> `/test -> scheduleTest` entrypoint before naming a
   job.
9. Treat direct order-level proof as highest-confidence evidence.
   If the final report SQL cannot be located, say the report mapping is an
   inference from matching totals instead of claiming a proved code path.
10. When only one residual remains, compute
   `report_value - reconstructed_value` and isolate the source column that
   contributes that exact same residual.

## Output standard

Close each investigation with:

1. the proved raw totals
2. the proved refund totals
3. whether each refund has external money-flow proof or only system-state proof
4. the statistics-table or report-layer totals, if used
5. which part is direct proof and which part is inference
6. the exact residual and the most likely source column

Avoid statements like "it should be this" unless the underlying orders or
statistics rows have been shown.

## Common failure modes

- The report reads a statistics table while the raw trade tables are correct.
- Statistics rows are allocated across many parking lots or dimensions.
- Rounding is repaired unevenly and only selected channel columns are updated.
- Channel columns reconcile, but rolled-up totals such as `income`, `refund`,
  or `balance` stay stale because the repair path did not update those totals.
- `data_owner_id` or `data_owner_name` in a statistics table is null, so the
  real report grouping path is through `parking_lot`.
- A report column uses wallet virtual flow while another uses total income or
  balance.
- External bank or payment files can reconcile perfectly to raw successful
  trades while the business report excludes an operationally unresolved order,
  such as a charging prepay order stuck in `waiting` with no charge, no
  `trade_record`, and no refund.
- A refund or channel allowance refund can be marked successful in system tables
  while the bank/channel export has no matching outflow, refund row, reversal
  row, settlement adjustment, or external refund number. For account matching,
  treat that as a failed or externally unsettled refund until external evidence
  proves otherwise.
- Web test endpoints that trigger a schedule can return `"success"` even when
  the worker exits early due to a Redis lock. Verify by checking row
  fingerprints or aggregate changes, not only the HTTP response.

## References

Load [references/report-reconciliation-fast-path.md](references/report-reconciliation-fast-path.md)
for reusable SQL templates, evidence grading, and a reconciliation checklist.

Load [references/report-field-mapping.md](references/report-field-mapping.md)
when you need a fast reminder of how raw trade fields, refund fields,
statistics-table fields, and wallet ledger fields usually differ in meaning.

Load [references/parking-statistics-repair.md](references/parking-statistics-repair.md)
when working in `hr_parking_platform_service`, especially around
`jobStaTimeCard`, `jobStaParkingCard`, charging station statistics,
charging prepay start-failure orders, `/test -> scheduleTest`, or report
discrepancies where channel columns match but statistics totals do not. Also
load it when the user asks which schedule job should be rerun, whether
`jobStaChargingStation` or `jobStaBasicDataCharging` is the right layer, or why
`refund_list.commit_time` puts a refund into a different month.

Load [references/union-pay-allowance-reconciliation.md](references/union-pay-allowance-reconciliation.md)
when the mismatch involves UnionPay/云闪付 channel discounts, finance-provided
CSV/XLSX files, `x_union`, `statement_accounts`, `checkAccount.js`, or fields
such as `refund_fee`, `method_allowance`, and `refund_method_allowance`.
