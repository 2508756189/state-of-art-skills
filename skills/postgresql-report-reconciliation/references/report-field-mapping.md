# Report Field Mapping

Use this reference when the hard part is not SQL syntax but field semantics:

- which field is the real payment amount
- which field is wallet real vs wallet virtual
- whether a statistics row is raw or allocated
- whether a report column can be reconstructed directly from orders

## Evidence priority

Use these sources in this order:

1. raw trade and refund rows
2. wallet ledger rows such as `balance_log`
3. precomputed statistics tables
4. report SQL or logic resources
5. spreadsheet formulas

If layers 1 and 4 disagree, state the disagreement explicitly. Do not let a
statistics table override direct order-level evidence without explanation.

## Core raw fields

These names vary by schema, but the concepts are stable.

### Trade rows

- `actual_received`
  The amount charged in this payment event. Useful for channel income or order
  payment totals. Do not assume it is wallet virtual flow.
- `real_fee`
  The portion paid from real balance or real-money channel value.
- `virtual_fee`
  The portion paid from virtual balance or subsidy value.
- `method_allowance`
  Channel or method allowance. Keep it separate until the report formula proves
  it belongs in the target column.
- `price`
  Often the nominal price of the card or order. It can differ from both
  `actual_received` and `real_fee + virtual_fee`.

### Refund rows

- `refund_real_fee`
  Real-balance or real-money refund amount.
- `refund_virtual_fee`
  Virtual-balance refund amount.
- `refund_method_allowance`
  Reversed allowance amount. Do not net this into real or virtual unless the
  report formula says so.
- `refund_fee`
  Total refund amount in several parking-platform statistics jobs. It can
  include cash, virtual, and channel allowance refund portions. When a channel
  report column says it includes discounts or allowances, compare it with
  `refund_fee` or with the explicit sum of all refund components, not only
  `refund_real_fee`.

## Typical meanings by report concept

### Raw payment total

Usually rebuilt from:

- `sum(actual_received + method_allowance)` for successful trades
- minus `sum(refund_real_fee + refund_virtual_fee + refund_method_allowance)`
  for successful refunds when the report shows gross income minus refunds

For UnionPay/云闪付, a refund can be only an allowance reversal:
`refund_real_fee = 0` and `refund_method_allowance > 0`. Use
`refund_real_fee <> 0 OR refund_virtual_fee <> 0 OR refund_method_allowance <> 0`
or a `refund_fee <> 0` condition when the report is supposed to include these
rows.

### Wallet real flow

Usually rebuilt from:

- `sum(real_fee)` for wallet trades
- minus `sum(refund_real_fee)` for wallet refunds

### Wallet virtual flow

Usually rebuilt from:

- `sum(virtual_fee)` for wallet trades
- minus `sum(refund_virtual_fee)` for wallet refunds

### Wallet ledger flow

If `balance_log` exists, it can prove which portion actually hit wallet real or
virtual balances. Use it to confirm that an order with `actual_received = 120`
was split into, for example, `105 real + 15 virtual`.

Do not assume `balance_log.amount` equals virtual flow. It may equal the total
wallet deduction. Inspect `balance_attr.detail` when available.

## Statistics table cautions

### `income`, `refund`, `balance` are often allocated

Card and subscription products are commonly split across every bound parking
lot, area, or owner dimension. A row in `statistics_time_card` or
`statistics_parking_card` may be a fractional allocation, not a raw order.

### Owner columns may be unusable

If `data_owner_id` or `data_owner_name` is null in a statistics table, the real
grouping path may be:

`statistics row -> parking_lot_id -> parking_lot.data_owner_id`

### Channel columns may diverge from `income`

Some jobs repair rounding or residuals only in channel columns such as
`income_wallet_real` or `income_wallet_virtual`, but do not also repair
`income` or `balance`.

When this happens, always compare:

- `sum(income)`
- sum of channel income columns
- direct raw trade reconstruction

## Common reconstruction patterns

### Pattern 1: prove a report column from raw trades

Use this when the column is likely direct and not allocated:

```sql
select
  trade_type,
  method,
  count(*) as cnt,
  sum(actual_received) as actual_received,
  sum(real_fee) as real_fee,
  sum(virtual_fee) as virtual_fee
from app_schema.trade_list_internal
where status = 'success'
  and receive_time >= timestamp '<start>'
  and receive_time < timestamp '<end>'
group by trade_type, method
order by trade_type, method;
```

### Pattern 2: prove a residual

If the report difference is small and stable, isolate one suspect column:

`residual = report_value - reconstructed_value`

Then test whether one column or one subcomponent contributes that exact same
residual.

### Pattern 3: prove that a report uses virtual-only wallet flow

Use both raw trades and refunds:

```sql
select
  coalesce(sum(virtual_fee), 0) as trade_virtual_fee
from app_schema.trade_list_internal
where status = 'success'
  and method = 'wallet_pay'
  and trade_type = '<trade-type>'
  and receive_time >= timestamp '<start>'
  and receive_time < timestamp '<end>';
```

```sql
select
  coalesce(sum(refund_virtual_fee), 0) as refund_virtual_fee
from app_schema.refund_list
where status = 'success'
  and method = 'wallet_pay'
  and trade_type = '<trade-type>'
  and commit_time >= timestamp '<start>'
  and commit_time < timestamp '<end>';
```

If `trade_virtual_fee - refund_virtual_fee` matches the report sub-total, say
that the report is consistent with a wallet-virtual-flow interpretation.

## What to say in the answer

Use precise language:

- "Direct order-level proof"
- "Statistics-table proof"
- "Ledger confirmation"
- "Inference from matching totals"

Avoid vague wording like "probably" unless you cannot prove the final report
SQL and you state exactly what remains inferred.
