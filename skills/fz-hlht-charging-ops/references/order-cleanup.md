# Order Cleanup Reference

Use this when cleaning Fengze TLD/HLHT charging orders.

## Current Environment Caution

Cleanup is production-adjacent and the test environment uses the Fengze app host reached through JumpServer, not a direct shell by default. For host-side cleanup scripts:

- Enter `Qzfz_web_node_10.0.0.3` from the JumpServer menu.
- Work in `/data/projects/parking_platform_service`.
- Set/use `EGG_SERVER_ENV=prod-fz`.
- Inspect `.codex-*` scripts before running them; several are one-off probes or hardcoded to old order ids.
- Prefer a fresh, narrowly written inline Egg script over rerunning a historical cleanup script if the target order id differs.

## Read-Only Checks First

Start with exact keys when available:

- `charging_order.order_no = StartChargeSeq`
- connector id from `charging_port.device_no`
- TLD `TradeNo`
- platform `refund_no`

Minimum evidence to collect:

- `charging_order`: `status`, `pay_status`, `billing_status`, `price`, `paid_fee`, `pay_pre_fee`, `auto_refund_fee`, `charging_time`, `finish_time`, `stop_reason`, `snapshot`
- successful `internal_trade` / `out_trade`
- refund rows and TLD refund status
- recent `hlht_push_log` or request logs for start and refund

## Safe Cleanup Pattern

A TLD prepay order can usually be closed locally when all are true:

- start failed or no valid charging session was formed;
- TLD refund is proven successful, or the platform refund row proves success;
- `paid_fee` is zero after refund;
- no `charging_time`;
- no `snapshot.send_to_pile`;
- not a real ongoing charging session;
- the only remaining issue is dirty local state, such as `pay_status='uncleared'` or `billing_status='waiting'`.

Typical final local state:

- `status='finish'`
- `pay_status='completed'`
- `billing_status='finish'`
- `stop_reason='HLHT启动失败且TLD退款成功'`
- `snapshot.tld_start_failed_refunded` marker with refund identifiers

## Avoid

- Do not bulk-close higher-value historical orders without explicit approval.
- Do not infer money state only from `charging_order.paid_fee`; reconcile trade and refund records.
- Do not mark an order completed if it may have real charging duration or an active session.
- Do not overwrite unrelated snapshot fields.

## Code Fix Pattern

When fixing this class of bug in `parking_platform_service`:

- Put pure decision logic in `app/utils/tldPrepayHelper.js` when possible.
- Keep DB mutation in `app/service/tldPrepay.js`.
- Use a transaction and row locks around order/trade/refund rows.
- Preserve real charging sessions by checking `charging_time` and `snapshot.send_to_pile`.
- Add a targeted test or direct assertion for:
  - dirty `finish` order without charging session should close;
  - sent-to-pile order should not close;
  - order with charging time should not close;
  - order with remaining paid balance should not close.

## Verification

After cleanup, re-query:

- count of recent TLD/HLHT orders where `pay_status != 'completed'` or `billing_status != 'finish'`;
- count of `charging_order.status != 'finish'`;
- the exact touched order rows;
- refund/trade rows to confirm money state.
