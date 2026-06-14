# Parking Statistics Repair

Use this note for `hr_parking_platform_service` report mismatches around
`statistics_time_card`, `statistics_parking_card`,
`statistics_by_charging_station`, and charging income or refund residuals.

## What this incident proved

- `jobStaTimeCard` groups income by `receive_time` and refunds by `commit_time`.
- The production schedule test endpoint for `prod-hr` is
  `https://city.fzpark.cn/parking/service/test`.
- Local `http://127.0.0.1:60061/test` is not a safe assumption for production.
- `/test -> scheduleTest` may return `"success"` even when the job does
  nothing because the Redis lock prevented execution.
- In this codebase, per-channel columns can be correct while the rolled-up
  `income`, `refund`, or `balance` columns are stale.
- A bank or payment-channel file can match raw successful trades exactly while
  a charging report omits a paid prepay order that never actually started
  charging and has not been refunded.

## Repair workflow

1. Lock the date window and report filters first.
   Use absolute dates. For this incident the validation window was
   `2026-02-01` through `2026-04-30`.
2. Reconcile raw trades against statistics by `sta_date` plus `data_owner_id`.
   For time cards, use `trade_list_internal` income by `receive_time` and
   `refund_list` refunds by `commit_time`.
3. Compare channel columns before total columns.
   If channel columns match raw trades but `income` or `balance` does not,
   the remaining defect is likely in the statistics repair logic rather than
   in raw payment data.
4. Prove the schedule path is actually executing.
   Check row counts, row-id fingerprints, or aggregate values before and after
   a rerun. Do not trust `"success"` alone.
5. When the user explicitly asks to correct historical data, a bounded repair
   can safely recompute:
   `income = sum(income_* channels)`,
   `refund = sum(refund_* channels)`,
   `balance = income - refund`
   over the affected date range.
6. Re-run residual SQL and require zero residual rows before calling the fix
   complete.

## Charging start-failure prepay hangs

Use this path when the payment or bank flow is higher than the charging report
by the exact amount of one or a few charging payments.

### Symptoms

- `trade_list_out` shows a successful `pay_charging` payment.
- The matching internal trade is a charging prepay row.
- `charging_order.pay_status = 'completed'`, but `status = 'waiting'` or
  another non-finished state.
- `charging_time`, `finish_time`, and `charging_power` are empty or zero.
- No successful refund exists in `refund_list`.
- No charging settlement row exists in `trade_record` or the relevant
  post-charging ledger.
- The order snapshot or third-party response shows start-charge failure,
  non-success `SuccStat`, a failure reason, or a start sequence state that did
  not enter normal charging.

### Checks

Start from the external payment order number or the residual amount and time:

```sql
select
  o.id as out_trade_id,
  o.trade_no,
  o.trade_type,
  o.pay_type,
  o.method,
  o.status,
  o.actual_received,
  o.real_fee,
  o.total_refund_real_fee,
  o.receive_time,
  i.id as internal_trade_id,
  i.trade_type as internal_trade_type,
  i.rela_id as charging_order_id,
  i.rela_no as charging_order_no
from app_schema.trade_list_out o
join app_schema.trade_list_internal i on i.out_trade_id = o.id
where o.trade_no = '<external-pay-order-no>';
```

Then inspect the charging order and prove the absence of refund or charging
settlement rows:

```sql
select
  id,
  order_no,
  charging_station_name,
  status,
  pay_status,
  billing_status,
  price,
  paid_fee,
  pay_pre_fee,
  electric_paid,
  service_paid,
  auto_refund_fee,
  manual_refund_fee,
  charging_time,
  finish_time,
  charging_power,
  snapshot::text
from app_schema.charging_order
where id = '<charging-order-id>'
   or order_no = '<charging-order-no>';
```

```sql
select count(*) as refund_cnt, coalesce(sum(refund_real_fee), 0) as refund_real_fee
from app_schema.refund_list
where out_trade_id = '<out-trade-id>'
   or trade_id = '<internal-trade-id>'
   or rela_id = '<charging-order-id>';
```

```sql
select count(*) as trade_record_cnt
from app_schema.trade_record
where rela_id = '<charging-order-id>'
   or rela_no = '<charging-order-no>'
   or order_no = '<charging-order-no>';
```

### Interpretation

If the payment is successful, the charging order never starts, charging power
is zero, and no refund exists, call it a "paid charging prepay hang after
start-charge failure." It is not a bank-side mismatch. It is also not a normal
"charged but not completed" order unless the order has charging time, power, or
post-charging settlement evidence.

### Resolution guidance

Prefer the normal charging refund workflow after making the order eligible for
that workflow. In this codebase, the refund path may only accept split charging
internal trade types such as:

- `charging_pre_service`
- `charging_after_service`
- `charging_pre_electric`
- `charging_after_electric`

Older or unsplit rows using `charging_pre` can be rejected by the refund
controller as an unsupported trade type. For those rows, do not only patch
report totals or order amounts. First confirm the fee split from
`charging_order.electric_paid` and `charging_order.service_paid`, correct or
split the internal trade classification in a bounded way, then execute the
existing refund flow so `refund_list`, trade refund totals, and charging order
paid/refund fields stay consistent.

For the finance explanation, use wording like:

"The bank file and raw payment flow are consistent. The residual is a charging
prepay order: payment succeeded, start charging failed, no charging power or
settlement record was produced, and no refund was created. It should be handled
as an abnormal paid-but-not-charged order and refunded through the charging
refund workflow."

## Useful checks

- Missing same-day statistics after a successful trade usually means the
  schedule did not run or exited early.
- Residuals like `-100` or `-120` tied to a single channel usually indicate a
  missing row or an unprocessed rerun day.
- Small residuals such as `0.44`, `-0.14`, or `-1.22` with all channel diffs at
  zero point to stale total columns rather than wrong channel allocations.
- A single residual equal to one successful charging prepay amount usually
  means the payment layer is right and the charging order/refund state needs
  order-level inspection.

## Manual Statistics Rerun

When the platform exposes the test controller, the usual rerun request body is:

```json
{
  "test": "scheduleTest",
  "name": "jobStaAreaBlockStreet",
  "param": ["YYYY-MM-DD"]
}
```

The request path is typically `{domain}/service/test`. In HR/Fengze-style
deployments, confirm the route is internal or otherwise permitted before relying
on it.

Common schedule names from the reconciliation docs:

- `jobStaAreaBlockStreet` -> `statistics_by_area_block_street`
- `jobStaSubArea` -> `statistics_by_sub_area`
- `jobStaOwnerDeptAccount` -> `statistics_owner_dept_account`
- `jobStaParkingCard` -> monthly-card statistics
- `jobStaTimeCard` -> time-card statistics

If a rerun endpoint returns `"success"` but row fingerprints do not change, or
if it returns a generic internal error, inspect the production logs for the
specific schedule name. A real fix may be a missing SQL projection field such
as `refund_fee` in a nested subquery, not the rerun endpoint itself.

## HR charging bank-report residual: unsplit prepay rows

Use this path for `hr_parking_platform_service` when a CCB bank detail file
matches raw `trade_list_out`, but the report/accounting screen's charging
income is lower by exactly one charging payment, often `10.00`.

### Proven failure mode

- Bank detail CSV contains a successful `pay_charging` order.
- `trade_list_out` has the payment and no refund.
- `trade_list_internal` has a successful old unsplit row such as
  `trade_type = 'charging_pre'`.
- The charging order may already be manually repaired to `status = 'finish'`
  and `finish_time` may be in the target day.
- Daily charging station tables can show the repaired amount, for example
  `charging_basic_data.actual_receivable` and
  `statistics_by_charging_station.total_receivable` become `219.53`, while the
  accounting/report screen still shows `209.53`.
- Reason: that report path sums split charging internal trade types, not the old
  unsplit type. It counts `charging_pre_electric`, `charging_pre_service`,
  `charging_after_electric`, and `charging_after_service`, but misses
  `charging_pre` / `charging_after`.

### SQL checks

Start from the external payment order number:

```sql
select
  o.id as out_trade_id,
  o.trade_no,
  o.trade_type as out_trade_type,
  o.method,
  o.status as out_status,
  o.actual_received,
  o.total_refund_real_fee,
  o.receive_time,
  i.id as internal_trade_id,
  i.trade_type as internal_trade_type,
  i.real_fee,
  i.refund_real_fee,
  i.rela_id as charging_order_id,
  i.rela_no as charging_order_no,
  co.status,
  co.pay_status,
  co.price,
  co.paid_fee,
  co.electric_paid,
  co.service_paid,
  co.finish_time,
  co.charging_power
from app_schema.trade_list_out o
left join app_schema.trade_list_internal i on i.out_trade_id = o.id
left join app_schema.charging_order co on co.id = i.rela_id
where o.trade_no = '<bank-order-no>';
```

Prove whether the report split total is missing the old row:

```sql
select trade_type, method, count(*) as cnt,
       coalesce(sum(real_fee - refund_real_fee), 0) as net_real
from app_schema.trade_list_internal
where status = 'success'
  and method = 'ccb_pay'
  and receive_time >= '<date> 00:00:00+08'
  and receive_time < ('<date>'::date + interval '1 day')
  and trade_type like 'charging%'
group by trade_type, method
order by trade_type;
```

Compare split-only vs split-plus-old totals:

```sql
select 'split_only' as scope,
       coalesce(sum(real_fee - refund_real_fee), 0) as net_real
from app_schema.trade_list_internal
where status = 'success'
  and method = 'ccb_pay'
  and receive_time >= '<date> 00:00:00+08'
  and receive_time < ('<date>'::date + interval '1 day')
  and trade_type in (
    'charging_pre_electric', 'charging_pre_service',
    'charging_after_electric', 'charging_after_service'
  )
union all
select 'split_plus_old' as scope,
       coalesce(sum(real_fee - refund_real_fee), 0) as net_real
from app_schema.trade_list_internal
where status = 'success'
  and method = 'ccb_pay'
  and receive_time >= '<date> 00:00:00+08'
  and receive_time < ('<date>'::date + interval '1 day')
  and trade_type in (
    'charging_pre', 'charging_after',
    'charging_pre_electric', 'charging_pre_service',
    'charging_after_electric', 'charging_after_service'
  );
```

If the residual equals `split_plus_old - split_only`, the missing report amount
is caused by the unsplit charging trade type.

### Why splitting did not run

The split is performed by the `checkChargingPay` timer. It is normally scheduled
when:

- charging payment finishes and the order is already `finish`; or
- the charging order finish callback completes the order.

If the order was not a valid finished order when payment completed, or it was
later manually repaired by updating `status` / `finish_time`, no timer is
scheduled retroactively. The internal trade remains `charging_pre`, and report
paths that only count split charging types still miss it.

### Preferred repair sequence

1. Confirm no refund exists in `refund_list` and finance wants to recognize the
   payment rather than refund it.
2. Repair the charging order completion fields if needed:
   - `status = 'finish'`
   - `pay_status = 'completed'`
   - target-day `finish_time`
   - sensible `charging_time`, `price`, `paid_fee`, `electric_paid`,
     `service_paid`, and refund fields based on business confirmation.
3. Trigger the splitter instead of manually editing totals:

```json
{
  "test": "timerTest",
  "id": "checkChargingPay-<charging_order_id>",
  "event": "checkChargingPay",
  "content": { "charging_order_id": "<charging_order_id>" },
  "time": 1
}
```

Call it on HR production via:

```text
https://city.fzpark.cn/parking/service/test
```

4. Verify the internal trade changed from `charging_pre` to the correct split
   type. If `electric_price = electric_paid = 0` and `service_paid` carries the
   whole amount, the expected result is `charging_pre_service`.
5. Re-run daily charging statistics after the split if the report also uses
   charging day tables:

```json
{ "test": "scheduleTest", "name": "jobStaBasicDataCharging.js", "param": ["<date>"] }
```

```json
{ "test": "scheduleTest", "name": "jobStaChargingStation.js", "param": ["<date>"] }
```

```json
{ "test": "scheduleTest", "name": "jobStaChargingPeriod.js", "param": ["<date>"] }
```

### Verification standard

Close the incident only after all relevant layers match:

- Bank CSV order-level net amount matches `trade_list_out` net.
- `refund_list` proves whether the amount was refunded or not.
- Split-only charging internal trade total includes the repaired order.
- `charging_basic_data` / `statistics_by_charging_station`, if used by the
  screen, reflect the repaired amount.
- The accounting/report screen is re-exported or refreshed and the residual is
  zero.

Do not trust `scheduleTest` returning `"success"` alone. Always compare the
row's `trade_type` and aggregate totals before and after triggering the timer.
