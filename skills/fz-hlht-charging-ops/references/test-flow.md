# TLD-HLHT Test Flow

Use this before creating a Fengze TLD/HLHT charging test order.

## Current Environment Access

Do not assume direct SSH execution against the app host.

Current verified path:

1. Connect to JumpServer: `wangshuhui@192.168.1.100:12222`.
2. In the JumpServer menu, search `/10.0.0.3`.
3. Select `Qzfz_web_node_10.0.0.3`.
4. Work under `/data/projects/parking_platform_service`.
5. Use `EGG_SERVER_ENV=prod-fz` and `NODE_ENV=production` for Egg scripts.

If the local machine does not have `ssh`, Python `paramiko` can drive the interactive JumpServer shell. Plain `exec_command` may attach only to the menu layer and return no app-host output.

## Correct Sequence

1. Choose a connector based on HLHT status definitions.
   - `Status=2` means occupied but not charging and can be a plugged-in candidate.
   - Avoid `Status=0`, `Status=255`, and `Status=3` unless intentionally testing failure/active-session behavior.
   - Treat `LockStatus=0` and `ParkStatus=0` as unknown.
2. Call `query_equip_auth`.
3. Call `query_equip_business_policy`.
4. Create the local `charging_order`.
   - `order_no` must equal `StartChargeSeq`.
   - Snapshot should preserve HLHT context and TLD prepay config.
5. Call TLD `trade_pre_create`.
6. If and only if TLD returns payment parameters, send the payment URL/link to the user.
7. Wait for TLD payment notification or confirm with `trade_query`.
8. On payment success, platform calls:
   - standard `query_start_charge`, or
   - TLD extension `query_start_charge_with_car` only if configured and supported.
9. Do not call the order "started" from `query_start_charge` alone:
   - `TRADE_SUCCESS` means payment succeeded only.
   - `query_start_charge` with `SuccStat=0` and `StartChargeSeqStat=1` means the start request was accepted and is still starting.
   - Real charging requires `StartChargeSeqStat=2` from start notification or charge-status query.
10. Follow:
   - `notification_start_charge_result`
   - `notification_equip_charge_status`
   - `notification_stop_charge_result`
   - `notification_charge_order_info`
11. Confirm refund or final settlement.

## Existing Remote Script

If present, prefer the existing production script for controlled test order creation:

`/data/projects/parking_platform_service/.codex-create-formal-tld-order-param.js <ConnectorID>`

Known behavior from current Fengze testing:

- It accepts the connector as the first argument.
- It creates an HLHT order and calls TLD `trade_pre_create`.
- It should not directly start charging before payment.
- It prints `CODEX_REFS`, `CODEX_ORDER_RESULT`, and `CODEX_RESULT`.
- `CODEX_RESULT.pay_params` is the transient payment URL.
- It sets expected start payload after payment with `StartChargeSeq`, `ConnectorID`, empty `QRCode`, and `PhoneNum`.

Inspect the current remote script before running it because `.codex-*` scripts may be excluded from local downloads and may drift. Older scripts such as `.codex-create-formal-tld-order.js`, `.codex-release-7205-and-create.js`, `.codex-start-variants.js`, and `.codex-tld-start-schema-probe.js` may be historical probes, hardcoded cleanup tools, or one-off tests.

## Current 3702121187205 Preflight

Before starting a new `3702121187205` order, verify:

- `charging_port.device_no='3702121187205'` exists.
- No local `charging_order` on that port is `waiting` or `charging`.
- `charging_port.using_status` may be `occupy` when HLHT `Status=2`; this is not by itself a blocker.
- Cached `options.hlht_status.Status=2` means occupied/not charging and can be valid if the vehicle is plugged in.
- Cached `options.hlht_equip_auth.SuccStat=0` means the latest stored auth succeeded.

If using a live Egg preflight, avoid calling nonexistent helper names; in this codebase `queryStationStatusByConnectorId` was not present during the 2026-05-28 check.

## Chinese Plate Encoding

Chinese license plates are business data, not cosmetic text. Do not avoid Chinese just because shell output is mojibake.

Rules:

- If the real test plate is `闽A88888`, all request bodies and generated Postman environments must preserve `闽A88888`.
- Never downgrade to `?A88888`, `MINA88888`, or `TESTFZ01` unless the user explicitly asks for a non-Chinese test plate.
- When generating files from Windows shells, write UTF-8 files directly or use Unicode escapes such as `\u95fdA88888`.
- Verify by checking code points. `闽A88888` should be `95fd 41 38 38 38 38 38`.
- If terminal display is wrong but the JSON file has the correct code points, keep the file and note it is display-only mojibake.

## Current Known Good Test Command

From the app directory:

```bash
cd /data/projects/parking_platform_service
node .codex-create-formal-tld-order-param.js 3702121187205
```

Expected current successful prepay shape:

- `CODEX_ORDER_RESULT.success=true`
- `order_no` / `StartChargeSeq` like `MA34J0D37...`
- `CODEX_RESULT.prepay_success=true`
- `CODEX_RESULT.tld_trade_no` like `CZZS...`
- `CODEX_RESULT.platform_trade_no` like `P...`
- `CODEX_RESULT.pay_params` is an Alipay WAP URL with the test amount.

After giving the payment URL to the user, wait for payment. Then verify the TLD callback or run a targeted trade query before claiming start-charge has happened.

## Failure Interpretation

- `trade_pre_create` returning `Ret=500` blocks the flow before payment and start.
- `query_start_charge` business failure after payment should trigger retry and then refund.
- `query_start_charge` returning `SuccStat=0` does not prove the pile started. If a later `notification_start_charge_result` has `StartChargeSeqStat=4`, treat it as ended/not charging.
- `StartChargeSeqStat=4` with `IdentCode=28` maps to "账户异常" in the current code. The TLD prepay document does not define why; ask TLD whether `Mobile`, the paid account, the prepay ledger, or account binding failed.
- `StartChargeSeqStat=5` plus missing/empty `ConnectorID` usually means unknown/no valid charging session for that start sequence; record it clearly.
- `Status=2` from station status is not contradictory with a failed `StartChargeSeq`.
- `RRC-213` / "已记账的充值订单为空，不允许退款" after a paid-but-not-started test means TLD does not see a refundable charged ledger for `trade_refund`. Do not keep retrying the same refund blindly; ask TLD whether this case auto-releases, needs a reversal/close API, or requires backend handling.

## TLD Prepay Field Notes

- `Mobile` belongs to `trade_pre_create`; it is documented as a partner user unique identifier of digits and letters. A phone number is syntactically valid, but the document does not prove it is accepted as a TLD account binding key.
- `PhoneNum` belongs to TLD's HLHT `query_start_charge` extension; use the same value as `Mobile` for the current personal-payment flow.
- `PrepaidType=1` is the current default for automatic-refund prepaid charging.
- The prepay document says `trade_refund` is used after receiving a finished charging order for balance refund. If no charging order/ledger exists upstream, refund failure can be expected and needs TLD clarification.

## TLD Escalation Template

Use this wording when payment succeeds but start does not reach charging:

`StartChargeSeq=<seq> trade_query 已返回 TRADE_SUCCESS，query_start_charge 返回 SuccStat=0、StartChargeSeqStat=1，但随后 notification_start_charge_result 推送 StartChargeSeqStat=4、IdentCode=28。请确认 IdentCode=28 在预充值启充场景下的准确原因；Mobile=<mobile> 是否必须绑定你们账户或支付账户；以及这类已支付但未形成充电/记账单的订单应走自动释放、撤销关单，还是其它退款接口。`

## Payment-Link Safety

- Only send a payment URL after confirming it came from the latest intended `trade_pre_create`.
- Include the `StartChargeSeq`, connector, and amount in the operator-facing summary.
- Do not reuse an older payment URL.
- If a start test fails after payment, immediately track refund status.

## After Test

Verify:

- no `charging_order.status != 'finish'` remains unless actively charging;
- no TLD/HLHT recent dirty orders remain;
- payment and refund rows match the expected amount;
- connector status changed as expected or is explainable from HLHT definitions.
