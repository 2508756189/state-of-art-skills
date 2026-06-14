---
name: "fz-hlht-charging-ops"
description: "Use for Fengze charging production triage and TLD-HLHT or local-payment charging work: checking four-wheel or two-wheel charging order states, payment closure, parking-fee waiver failures, HLHT Status/LockStatus/ParkStatus, TLD prepay/refund, UMS refund stuck states, start-failed cleanup, and safely deploying parking_platform_service charging fixes."
---

# FZ HLHT Charging Ops

Use this skill for Fengze charging issues that involve `parking_platform_service`, HLHT, TLD prepay, two-wheel charging/payment closure, charging orders, connector status, refunds, or production test orders.

For end-to-end new parking-lot setup, barrier binding, billing/payment configuration, or charging-enabled lot onboarding, start with `fz-lot-onboarding`; use this skill for the charging-specific add-on and incident details.

Pair it with:

- `production-ops` for server access, backup, upload, restart, and smoke tests.
- `fz-node-service-deploy-checklist` for Fengze code/SQL uploads, process-model discovery, restart, and smoke verification.
- `postgresql-debug` for live PostgreSQL inspection and narrow writes.
- `doc` or `pdf` when reading vendor DOCX/PDF specs.

Do not store or repeat production passwords, Redis secrets, DB passwords, API secrets, or payment links in skill files or final summaries unless the user explicitly needs a transient payment URL from a live test.

## Current Fengze Test Environment

This environment is not a direct SSH-to-app-host flow. Current working access is:

- Local workstation: Windows PowerShell.
- Best server command path: Python `paramiko` helper from `production-ops`, using `D:\下载\wsh_new.jumpserver.pem`.
- If `paramiko` is missing, install it once with `python -m pip install paramiko`; only fall back to WinSCP/manual shell if Python or install fails.
- Use WinSCP/SFTP primarily for file transfer, not first-choice remote command execution.
- Bastion entry: JumpServer menu at `wangshuhui@192.168.1.100:12222` using the local JumpServer key.
- After login, search `/10.0.0.3` and choose `Qzfz_web_node_10.0.0.3`.
- App path after entering the host: `/data/projects/parking_platform_service`.
- Runtime environment: `EGG_SERVER_ENV=prod-fz`, `NODE_ENV=production`.
- Logs: `/data/logs/parking_platform-prod-fz`.

Do not assume a normal direct `ssh host command` works through the bastion. Do not spend tokens cycling through SSH, WinSCP, and ad hoc probes. Start with the Python JumpServer helper; use command files for multi-step commands.

If VPN is disconnected, both JumpServer and direct host ports can simply time out. Confirm TCP reachability before debugging credentials. If the JumpServer key is missing and the user explicitly approves temporary root access, direct SSH/SFTP to the host is acceptable, but preserve the app file owner and restart as the runtime user.

## Core Rules

- Treat four-wheel TLD charging as an HLHT main flow with TLD prepay/refund extensions.
- Always distinguish platform order state from connector physical state.
- Always distinguish `trade_query` payment success from charging success. `TRADE_SUCCESS` only proves payment; the order is not charging until `notification_start_charge_result` or `query_equip_charge_status` reaches `StartChargeSeqStat=2`.
- Read the HLHT status definitions before interpreting `Status`, `LockStatus`, or `ParkStatus`; do not infer from parking-lot intuition.
- Read production state before writing. If a write is needed, make it narrow, explain the filter, and verify after.
- Never start a paid test order unless the current upstream state and expected refund path are understood.
- For live tests, create only one intended small-value order at a time and keep the connector, `StartChargeSeq`, TLD trade no, and payment URL tied together.
- Do not replace Chinese license-plate prefixes with ASCII because of terminal mojibake. A plate like `闽A88888` must remain a Chinese-prefix plate in request data; fix the encoding path instead.
- For production deploys, back up each remote file, upload only intended files, run remote syntax checks, restart with the existing environment, and verify port/process.
- PostgreSQL internal schemas such as `pg_temp_*`, `pg_toast`, and `pg_toast_temp_*` are not server temp files to delete; clean only confirmed project temp artifacts such as `.codex-*` scripts or misplaced backup files.
- Fengze four-wheel charging may run either TLD third-party prepay or the older local platform payment path. For local platform payment, `ums_pay` refunds must stay on the UMS channel; do not let them fall through to wallet, charging-card, or enterprise-account balance refund logic.
- For branch-like payment/refund bugs, compare sibling branches for missing `break`, missing `return`, wrong query key, or fallthrough before redesigning the charging/refund chain.

## Fast Workflow

1. Identify the incident key:
   - `StartChargeSeq` / `order_no`
   - `ConnectorID`
   - station id
   - trade no / refund no if payment or refund is involved
2. Query platform facts:
   - `charging_order`
   - related `internal_trade`, `out_trade`, `refund`
   - `charging_port`, `charging_pile`, `charging_station`
   - `hlht_push_log` or equivalent request logs
3. Query or inspect upstream HLHT/TLD facts:
   - `query_station_status`
   - `query_equip_auth`
   - `query_equip_business_policy`
   - `trade_pre_create`
   - `notification_trade_result`
   - `query_start_charge`
   - `notification_start_charge_result`
   - `trade_refund` / `trade_refund_query`
4. Classify the problem:
   - payment pre-create failed
   - paid but start failed
   - refund requested but not completed
   - UMS/local-payment refund is stuck in `refund_list.processing`
   - charging parking-fee waiver did not apply at exit
   - refund completed but local order state dirty
   - connector physically occupied/offline/faulted
   - two-wheel data is mixed into an old table instead of the intended separate table
   - payment/refund branch fell through or called the wrong payment method
   - platform code handling gap
5. Only then choose the action:
   - record evidence only
   - clean a known failed/refunded test order
   - fix code
   - redeploy
   - run a controlled new test order

## Status Interpretation

Read [references/hlht-status.md](references/hlht-status.md) before making claims about connector availability.

Important reminders:

- `Status=2` means occupied but not charging. It can be a valid pre-start plugged-in state.
- `Status=1` means free; it is not necessarily the state you want for starting charge, because many scenarios require the gun to be inserted first.
- `LockStatus=0` and `ParkStatus=0` mean unknown, not normal.
- `Status=0` means offline; `Status=255` means fault.

## Order Cleanup

Use [references/order-cleanup.md](references/order-cleanup.md) when the user asks to clean current orders, close a stuck order, or fix dirty TLD/HLHT order state.

Cleanup candidates are usually start-failed, refunded prepay test orders where:

- no charging session formed;
- no `snapshot.send_to_pile`;
- no `charging_time`;
- refund succeeded or can be proven;
- remaining paid balance is zero;
- the order is only dirty in local `pay_status`, `billing_status`, or `stop_reason`.

Avoid bulk-changing real-value historical orders unless the user explicitly approves the exact set.

## Charging Parking-Fee Waiver

Use this path when a tester says a car charged successfully but still had to pay parking at exit.

Facts to prove first:

- `charging_order.status='finish'` and `pay_status='completed'`.
- `charging_order.rela_order_id` or `rela_order_no` points to the parking order, or at minimum the charging order has the same `parking_lot_id`, `plate_no`, and `plate_no_color`.
- `charging_order.parking_lot_id` is present. If missing, inspect the station/pile binding before changing historical orders.
- `ipms.base_config.key='charging_bonus'` contains the target parking lot id under `value.value`.
- `barrier_log.status='before_away'` for the parking order shows whether the barrier sent `allowance=0` or a positive allowance.

Important code locations:

- `app/controller/barrier.js`: `/barrier/beforeAway` applies the final exit price and should have a charging-waiver fallback when the barrier sends `allowance=0`.
- `app/service/chargingUtilsService.js`: `calcParkingBonusAllowance` should find the related finished charging order and compute the waiver; `sendBonusToBarrier` is only the proactive ticket-downstream path.
- Do not rely only on the barrier ticket route. In this deployment, `/crypto/barrier/UpTicketNo` may be unavailable on `barrier_gate_system`, so the main-platform `beforeAway` fallback is the critical protection.

Configuration for a new parking lot:

```json
{
  "value": {
    "<parking_lot_id>": { "range": "hour", "num": 720 }
  }
}
```

Use `{ "range": "all" }` only when the business really wants full waiver. After adding a lot, verify with a real or controlled parking order by posting `/barrier/beforeAway` with `allowance=0`; success evidence is response `price=0` and `barrier_log.data.charging_bonus` containing the charging order number and allowance.

If using the same historical parking order for a controlled simulation, explicitly reset only that order to `parking/uncleared` and restore or document its final `away/completed` state after the test.

## Local-Payment UMS Refund Stuck

Use this path when four-wheel charging is using the local platform payment method and the refund stays in "applying/processing".

Check:

- `refund_list.method='ums_pay'`, related `trade_type` such as `charging_pre_service`, and `status`.
- `refund_list.commit_time` and `receive_time`: both null on `processing` means it likely never completed channel submission.
- `app/schedule/refund.js`: the scheduler picks `status='waiting'`, not old `processing` rows. It should have a `break` after the `case 'ums_pay'` call to `this.service.umspay.refund(...)`; otherwise it can fall through into `card_pay` and incorrectly call the local charging-card refund path.
- Confirm whether the deployed file and running process match. A file may already be fixed while old `processing` rows still need a narrow retry.

Safe recovery pattern after code is fixed:

1. Verify there is no successful channel refund already recorded in `result_attr`.
2. For exact known stuck refund numbers only, change `processing` with null `commit_time` back to `waiting` and set `commit_time=now()` so the scheduler can pick it.
3. Let the scheduler submit the UMS refund.
4. Verify `refund_list.status='success'`, `receive_time` is populated, and `result_attr.errCode='SUCCESS'` or equivalent channel success fields are present.
5. If a temporary diagnostic `error_code/error_msg` was written before retry, clear it only after success so operations UI does not show a stale error.

## Correct Test Flow

Use [references/test-flow.md](references/test-flow.md) before starting or creating a TLD/HLHT test order.

High-level sequence:

1. Confirm candidate connector status from HLHT docs, not by guessing.
2. Run auth and business policy checks.
3. Create a local charging order with `order_no = StartChargeSeq`.
4. Call TLD `trade_pre_create`.
5. Only after `PayParams` is returned, send the payment link to the user.
6. After payment success, platform calls `query_start_charge`.
7. Treat `query_start_charge` `SuccStat=0` plus `StartChargeSeqStat=1` as "accepted/start pending", not success.
8. Follow start notification, real-time status, final order info, and refund.

Current TLD prepay caveats:

- `trade_pre_create.Mobile` is documented as a partner user unique identifier of digits and letters; a phone number is acceptable as an identifier, but the prepay document does not state whether it must be bound in TLD's account system.
- `PrepaidType=1` means automatic-refund prepaid charging and should be the default for the current flow.
- `IdentCode=28` is mapped in the current code as "账户异常", but the TLD prepay document does not explain the exact cause. Ask TLD whether the `Mobile`, paid account, prepay ledger, or account binding failed validation.
- `trade_refund` is documented for refund after receiving a finished charging order. If no charging ledger is formed, TLD may return "已记账的充值订单为空，不允许退款"; ask whether to wait for auto-release, use another reversal API, or have TLD handle it.
- TLD `trade_refund` refunds only a total amount. Local settlement must still split successful refunds across `charging_pre_electric` / `charging_pre_service` or legacy `charging_pre` records, update `refund_list`, and keep `OutRefundNo` idempotent. See [references/deployment-and-refund-notes.md](references/deployment-and-refund-notes.md).

Current controlled script preference:

- Prefer `/data/projects/parking_platform_service/.codex-create-formal-tld-order-param.js <ConnectorID>` when it exists.
- It accepts a connector argument and creates the local HLHT order plus TLD prepay.
- For the current repeated test connector, use `3702121187205` only after preflight proves no active local order and connector status is suitable.
- Do not run older hardcoded scripts without inspecting them; several `.codex-*` files are historical probes or cleanup scripts.

## Chinese Plate Encoding

When generating Postman environments, Node scripts, SQL snippets, or shell commands for plate tests:

- Preserve the actual plate value, for example `闽A88888`; do not silently change it to `MINA88888`, `?A88888`, or `TESTFZ01`.
- On Windows, avoid passing Chinese values through a PowerShell command string when the terminal code page may convert them to `?`.
- Prefer UTF-8 files, JSON files, or Unicode escapes such as `\u95fdA88888` when writing generated artifacts.
- Verify the stored bytes or code points after writing. For `闽A88888`, the first code point must be `0x95fd`.
- If display output is garbled but raw bytes/code points are correct, call it a display issue and keep the Chinese plate value.

## Code Areas

Primary files in `parking_platform_service`:

- `app/service/hlhtCharging.js`: HLHT security envelope, station status, auth, policy, start/stop, notifications.
- `app/service/tldPrepay.js`: TLD prepay, trade query, refund, refund query, refund notification handling.
- `app/utils/tldPrepayHelper.js`: TLD prepay builders, status mappers, refund/stop helpers.
- `app/service/pay.js`: payment completion and `postHlhtChargingApi` start flow.
- `app/timer/queryTldRefund.js`: refund query compensation.
- `app/schedule/hlhtQueryStationsStatus.js`: periodic station status sync.
- `app/controller/barrier.js`: `/barrier/beforeAway` exit pricing and charging parking-fee waiver fallback.
- `app/service/chargingUtilsService.js`: charging order to parking order matching, barrier ticket sending, and parking-waiver calculation.
- `app/schedule/refund.js`: queued local refund submission; verify `ums_pay` does not fall through to local balance/card refund branches.

For two-wheel charging closure, keep the old frontend request/response shape where practical, but route persistence into the separate two-wheel tables. Prove the whole path from pay endpoint, callback settlement, start/finish state, refund handling, and smoke routes rather than checking one controller only.

## Production Deployment Notes

- Use the app's existing runtime user and environment.
- For Fengze `parking_platform_service`, verify the real environment before restarting; this deployment has used `EGG_SERVER_ENV=prod-fz`.
- Run local and remote `node -c` on changed JS files.
- On the server, root's non-interactive PATH may not include Node. Use the deployed runtime path such as `/data/nodejs/node-v16.20.2-linux-x64/bin/node`, and run npm commands with that bin directory prepended to PATH.
- Preserve remote app file ownership and mode. Current `parking_platform_service` files have used `cloudlogin:cloudlogin 644`; if uploading as root, restore owner/mode from the timestamped backup before restart.
- Restart `parking_platform` as the runtime user, not as root. Keep `NODE_ENV=production` and `EGG_SERVER_ENV=prod-fz`.
- Record backup file paths and post-restart evidence.
- If startup fails, distinguish code syntax/runtime errors from wrong environment config.

For the exact checklist and evidence to collect, read [references/deployment-and-refund-notes.md](references/deployment-and-refund-notes.md).

## Verification Checklist

- HLHT status interpretation cites the status table, especially for `Status=2`, `LockStatus=0`, and `ParkStatus=0`.
- DB facts prove whether the platform has a stuck order.
- Payment/refund facts prove money state before changing order state.
- Any production write has a precise filter, transaction, and post-write verification.
- Code fixes include at least focused syntax checks and a small targeted test or direct assertion when the full Egg test harness is unavailable.
- Final answer separates “platform clean”, “upstream connector state”, and “next safe test action”.
