# UnionPay Allowance Reconciliation

Use this when UnionPay/云闪付 income looks higher in the external file than in
the system report, especially when the residual equals a channel discount or
allowance refund.

Core rule: account reconciliation is governed by the external money flow. A
system-side allowance refund is not enough to reduce the channel/bank balance
unless the external statement, settlement detail, or channel response proves a
matching refund, reversal, or adjustment.

## Source Notes

The local document `D:\电动车充电对接文档\主平台直连模式\新脚本对账相关.docx`
states that UnionPay/云闪付 often has no automatic channel-account API. Finance
may provide CSV/XLSX files that are imported into a temporary table such as
`x_i_union`, then inserted into `x_union` before manual reconciliation.

The same document says UnionPay refund totals may need to include channel
allowance refunds, but one example filter used only `refund_real_fee <> 0`.
That condition misses pure allowance refunds. Whether those allowance refunds
should reduce the external balance still depends on the external money-flow
evidence gate below.

## Fast Diagnosis

1. Treat the external UnionPay file as gross channel evidence first.
   If the file has no refund row for a channel allowance reversal, do not assume
   the system is short. Check system refund rows, but keep the external gross
   balance unchanged until an external refund/adjustment is proved.
2. Query successful UnionPay payments with allowance fields:

```sql
select
  sum(actual_received) as actual_received,
  sum(coalesce(method_allowance, 0)) as method_allowance,
  sum(coalesce(actual_received, 0) + coalesce(method_allowance, 0)) as gross_with_allowance
from ipms.trade_list_internal
where method = 'union_pay'
  and status = 'success'
  and data_owner_id = '<owner-id>'
  and receive_time >= timestamp '<start>'
  and receive_time < timestamp '<end>';
```

3. Query refunds with an allowance-aware condition:

```sql
select
  sum(coalesce(refund_fee, 0)) as refund_fee,
  sum(coalesce(refund_real_fee, 0)) as refund_real_fee,
  sum(coalesce(refund_virtual_fee, 0)) as refund_virtual_fee,
  sum(coalesce(refund_method_allowance, 0)) as refund_method_allowance
from ipms.refund_list
where method = 'union_pay'
  and status = 'success'
  and data_owner_id = '<owner-id>'
  and commit_time >= timestamp '<start>'
  and commit_time < timestamp '<end>'
  and (
    coalesce(refund_real_fee, 0) <> 0
    or coalesce(refund_virtual_fee, 0) <> 0
    or coalesce(refund_method_allowance, 0) <> 0
    or coalesce(refund_fee, 0) <> 0
  );
```

4. Check whether each refund has external money-flow proof:

- external file row for refund, reversal, adjustment, or allowance return
- channel settlement detail showing the amount left the merchant account
- channel response fields such as an external refund id, settle reference, or
  target order id that can be found in the merchant backend

If `refund_attr` and `result_attr` are empty, the channel query still reports
`refundAmount = 0`, or the finance export has no refund/adjustment row, do not
deduct that refund from the external balance. For reconciliation, treat it as
failed or externally unsettled even if `refund_list.status` currently says
`success`.

5. Reconcile net amount:

```text
If external refund/adjustment is proved:
  external net = external gross file amount - proved external refund/adjustment
  system net should use the same refund/adjustment.

If external refund/adjustment is not proved:
  external net = external gross file amount
  do not reduce the report just because system tables have a success refund row.
```

For thread `019e95d1-9949-7223-b0e3-f85501b732e0`:

```text
external gross = 9.00
refund_method_allowance = 3.00
refund_attr = {}
result_attr = {}
original channel query refundAmount = 0
no external refund/adjustment row in the available finance export
for account matching, keep external net = 9.00
marking the system refund failed and rerunning statistics produced report net = 9.00
residual = 0.00
```

Current case note:
Current rule: do not explain this as cash already refunded unless external
evidence proves the outflow. Without external refund or adjustment evidence,
classify it as an externally unproved allowance-refund path and keep the
external balance gross for account matching.

## Code And Script Checks

When updating scripts, check all layers that can encode the old cash-only
filter:

- `app/service/checkAccount.js`
- a shared amount helper such as `app/utils/checkAccountAmount.js`
- `statement_accounts` and `statement_accounts_<channel>` matching SQL
- `x_union` / `x_i_union` import SQL
- statistics jobs such as `jobStaAreaBlockStreet.js`, `jobStaParkingCard.js`,
  and `jobStaTimeCard.js`

For statistics jobs, income may already include `method_allowance` while refund
still uses only `refund_real_fee + refund_virtual_fee`. If the report's refund
column should include channel discounts, use `refund_fee` or include
`refund_method_allowance`.

For account-facing outputs, do not include `refund_method_allowance`
unconditionally. Split the logic by reconciliation goal:

- business revenue reports may show the business adjustment if that is the
  report contract
- bank/channel account matching should include it only when the external
  refund/adjustment is present, or after the failed/unsettled refund state has
  been corrected and the day has been rerun

If a nested SQL subquery exposes `bt.refund_fee` in the outer query, verify the
inner `select` actually projects `refund_fee`; otherwise a manual rerun can fail
with a generic internal error and a production log like
`column bt.refund_fee does not exist`.

## Explanation Template

Use this shape for finance/operations:

```text
If external refund/adjustment evidence exists:
  The UnionPay file shows gross payment <gross>, and the external settlement
  also shows refund/adjustment <refund>. Reconciliation net is
  <gross> - <refund> = <net>.

If external refund/adjustment evidence is missing:
  The UnionPay file shows gross payment <gross>, but no external refund,
  reversal, settlement adjustment, or external refund number was found for
  <refund>. For account matching, keep the channel amount at <gross> and treat
  the system refund as failed or externally unsettled until the channel proves
  the outflow.
```
