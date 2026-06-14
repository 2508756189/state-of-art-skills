# Fengze TLD/HLHT Deployment And Refund Notes

Use this reference when deploying Fengze four-wheel charging fixes or auditing TLD prepay/refund behavior.

## Deployment Notes

- Confirm VPN/network first. If JumpServer and direct host ports time out together, treat it as reachability, not a credential failure.
- Prefer JumpServer with the configured key. If the key file is missing and the user explicitly allows temporary direct root access, use direct SSH/SFTP only for host operations.
- Do not run the service as root. Use root only to upload/replace files when needed, then restore the original owner/mode and restart as `cloudlogin`.
- Preserve remote files with timestamped backups before overwrite, for example `file.js.bak_YYYYMMDD_HHMMSS`.
- Download backup copies locally when feasible.
- Verify upload by checksum and `stat`. The app files should keep the previous owner and mode.
- Root's non-interactive PATH may not include Node. Use `/data/nodejs/node-v16.20.2-linux-x64/bin/node --check <file>` for remote syntax checks.
- For `npm run stop/start`, prepend `/data/nodejs/node-v16.20.2-linux-x64/bin` to PATH and export `NODE_ENV=production` plus `EGG_SERVER_ENV=prod-fz`.
- Verify a restart with old/new master PID, port `60061`, and a local smoke test. A `200` login/permission response from `/` proves the Egg app is mounted.
- Check `/home/cloudlogin/logs/master-stderr.log` and fresh entries in `/data/logs/parking_platform-prod-fz/common-error.log` after restart. Separate old historical errors from post-restart errors by timestamp.

## TLD Refund Accounting Notes

- TLD `trade_refund` accepts and returns only a total refund amount. It does not split electric/service fee.
- Platform local settlement must still split the successful TLD refund into local accounting rows:
  - electric side: `charging_pre_electric` / `charging_after_electric`
  - service side: `charging_pre_service` / `charging_after_service`
  - legacy fallback: `charging_pre` / `charging_after` as service-side trade
- Use order fields to calculate expected local refundable components:
  - electric: `electric_paid - electric_price`
  - service: `service_paid + service_bonus - service_price`
  - fallback only when component fields are unavailable: `paid_fee + service_bonus - price`
- Do not silently accept a TLD refund amount greater than local refundable balance or the remaining internal trade balance.
- Write visible `refund_list` rows for failures and successes. Failure rows help operations and reports see that TLD refund was attempted but did not settle locally.
- Use `OutRefundNo` as the TLD refund idempotency key. Duplicate success notifications must refresh result data without applying money twice.
- A start-failed paid order can only be locally cleaned as refunded after TLD refund success or another proven upstream release path.

## Local UMS Charging Refund Notes

Use this when Fengze four-wheel charging has returned to the original local platform collection path instead of TLD third-party prepay.

- `refund_list.status='waiting'` is the normal queue state for `app/schedule/refund.js`; `processing` rows are not picked again by the scheduler.
- For `ums_pay`, the schedule must stop after `this.service.umspay.refund(...)`. A missing `break` after the `ums_pay` case can fall through into `card_pay` and call `balance.refundChargingCard(refund)`, which is the wrong local balance path for UMS payments.
- A stuck `processing` row with null `commit_time` and null `receive_time` usually means channel submission did not finish or the row was left mid-flow. Do not bulk reset all processing rows.
- Recovery after code verification: select exact refund numbers, confirm no success result exists, set only those rows back to `waiting` with a current `commit_time`, then let the scheduler submit them.
- Success evidence for UMS refunds is `refund_list.status='success'`, populated `commit_time/receive_time`, and channel `result_attr` containing UMS success fields such as `errCode='SUCCESS'`, `refundStatus='SUCCESS'`, and the actual refund amount.
- If temporary diagnostic text was written to `error_code/error_msg`, clear it only after the refund succeeds.

## Charging Parking-Fee Waiver Notes

Use this when a successful four-wheel charging order should waive parking but the tester still sees a parking fee at exit.

- Required data binding:
  - `charging_order.status='finish'`
  - `charging_order.pay_status='completed'`
  - `charging_order.rela_order_id` / `rela_order_no` points to the parking order, or at least same `parking_lot_id`, `plate_no`, `plate_no_color`
  - `charging_order.parking_lot_id` is populated
- Required config:
  - `ipms.base_config.key='charging_bonus'`
  - target lot under `value.value[parking_lot_id]`
  - example: `{ "range": "hour", "num": 720 }`
- Do not assume barrier-side coupon delivery is enough. If `/crypto/barrier/UpTicketNo` is absent or fails, the main-platform `/barrier/beforeAway` fallback should still compute a waiver when the barrier sends `allowance=0`.
- Verification evidence:
  - simulate or observe `/barrier/beforeAway` with `allowance=0`
  - response has `price=0` for a small unpaid parking fee
  - `barrier_log.data.charging_bonus` records the charging order number and waiver amount
  - the parking order ends as `away/completed`

## Verification Snippets

Use exact paths on the host:

```bash
cd /data/projects/parking_platform_service
/data/nodejs/node-v16.20.2-linux-x64/bin/node --check app/service/tldPrepay.js
/data/nodejs/node-v16.20.2-linux-x64/bin/node --check app/service/hlhtCharging.js
su - cloudlogin -c 'export PATH=/data/nodejs/node-v16.20.2-linux-x64/bin:$PATH; export NODE_ENV=production; export EGG_SERVER_ENV=prod-fz; cd /data/projects/parking_platform_service && npm run stop && npm run start'
ss -lntp | grep 60061
curl -s -o /tmp/parking_platform_root.out -w '%{http_code}' http://127.0.0.1:60061/
```

Expected smoke result for `/` without login is HTTP `200` with a no-permission/need-login JSON response.
