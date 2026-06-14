---
name: bkv
description: Fengze BKV two-wheel charging development and field-test operations. Use when working on the Fengze parking platform BKV charging flow, including charging strategy options, /bkv/startCharge and /xcx/bkv APIs, Postman field testing, PostgreSQL data setup, fz_parking_platform_log troubleshooting, charging_push_log/order reconciliation, BKV protocol code interpretation, monthly-card/charging-card/whitelist charging, payment/refund behavior, frontend/mini-program handoff, or deployment-version checks for this project.
---

# BKV Two-Wheel Charging

Use this skill as the field notebook for the Fengze BKV two-wheel charging work. It captures the local project layout, the current implementation state, formal HTTP flows, frontend/mini-program interface boundaries, database/log lookup patterns, and known live-device failure signatures.

## First Moves

1. Work from the active Fengze workspace the user gives. On this machine, the common workspace is `D:/电动车充电对接文档/甘孜cpw跳板接主平台项目`; do not assume the older `C:/Users/mm/Desktop/丰泽` path exists.
2. For code questions, inspect local files first; do not assume the deployed service matches local code.
3. For live testing, distinguish three layers: platform route/controller, middleware/device dispatch, and BKV device callback.
4. If `/bkv/startCharge` returns `{"success":false,"error":"无响应"}` in about 1 ms, treat it as likely platform route miss or stale deployment, not a device timeout.
5. Prefer checking logs before retrying real equipment; avoid repeated live starts while an order may still be charging.
6. When changing `parking_platform_service` BKV code, also inspect the `barrier_system` middleware for matching protocol assembly/parsing, callback routes, message logging, and timeout behavior.

## Reference Map

Load only the file needed for the current task:

- `references/project-context.md`: project paths, modified files, DB/log DB, stations, piles, documents, frontend/mini-program API state, and strategy configuration.
- `references/http-test-flow.md`: formal BKV API flow, Postman bodies, true-device operation order, xcx paid-order flow, identity-channel test flow, and expected checks.
- `references/db-and-logs.md`: SQL snippets for orders, push logs, request logs, message logs, resources, time cards, whitelist, charging cards, and deployment-version diagnosis.
- `references/implementation-notes.md`: strategy logic, identity channels, billing/refund rules, protocol-friendly names, interface boundaries, and known remaining scope.

## Core Rules

- There are exactly three user-paid strategies in this project: `duration`, `electricity_service`, and `per_use`.
- Monthly card, charging card, and whitelist are identity/payment channels, not additional charging strategies.
- BKV service-fee ladder protocol fields `0x80/0x81/0x82/0x83/0x89` are intentionally out of current scope; electricity and service prices live in `ChargingStrategy.options`.
- Avoid adding normal DB columns unless absolutely necessary. Prefer JSON config under `station.options`, `ChargingStrategy.options`, `ChargingOrder.snapshot`, `base_config.value`, and related `options` fields.
- For one station with multiple strategies, configure `station.options.charging_strategy_ids` as a JSON object mapping charge mode to strategy id.
- `port_no` for real BKV port `0` should be sent as string `"00"` when calling HTTP APIs.
- Logs must support field troubleshooting: platform request, device packet, middleware callback, order, push log, trade record, and charge-end settlement should be reconcilable by order number/device/trade number.
- Treat `parking_platform_service` and `barrier_system` as one BKV chain. Platform-only fixes can still fail if middleware command fields, callback routes, or message logs are stale.

## Current Two-Wheel Independent Module State (2026-06-01)

This section supersedes the older BKV-named business API guidance when the task is about the new independent two-wheel charging module.

- Business module name is two-wheel charging, not BKV. BKV is only one `device_brand` value, normally `device_brand='BKV'`.
- New backend/admin APIs use `/twoWheel/*`; do not add `/admin` in the path.
- New mini-program APIs use `/twoWheel/xcx/*`, not `/xcx/twoWheel/*` and not `/xcx/bkv/*`.
- Legacy `/bkv/*` and `/xcx/bkv/*` APIs may still be useful as protocol/reference code, but new frontend and mini-program handoff should document and implement `/twoWheel/*`.
- Two-wheel charging must be independent from four-wheel car charging. Do not route new two-wheel payment through `/pay/charging`; use dedicated two-wheel payment/order interfaces and `two_wheel_*` tables.
- Independent tables currently planned/implemented: `two_wheel_station`, `two_wheel_pile`, `two_wheel_port`, `two_wheel_order`, `two_wheel_strategy`, `two_wheel_whitelist`, `two_wheel_month_card_config`, `two_wheel_month_card`, `two_wheel_recharge_card`, `two_wheel_recharge_card_log`, `two_wheel_pay_order`.
- Every new `two_wheel_*` table should include `id`, `created_at`, `updated_at`, `deleted_at`, and `deleted`.
- A station can contain piles from multiple brands. Treat station `device_brand` as default/display only; actual device dispatch should prefer `two_wheel_pile.device_brand` or `two_wheel_port.device_brand`.
- Avoid duplicate schema fields in the new design: use `two_wheel_strategy_ids`, not both `strategy_ids` and `two_wheel_strategy_ids`; use `charging_port_num`, not both `port_count` and `charging_port_num`; order charging start time is `charging_time`, not a separate `start_time`.
- Order records should keep charging lifecycle and settlement context, including `charging_time`, `finish_time`, `charging_duration`, `charging_power`, price detail fields, `refund_fee`, `stop_reason`, `trade_no`, `device_order_no`, and `snapshot`.
- `update` endpoints are not rename-only. Except for `id`, callers may submit any supported business fields for that table; omitted fields remain unchanged.
- Current handoff docs: `二轮充电文档/二轮充电前端小程序接口说明v2.md` and `二轮充电文档/二轮充电独立模块建表SQL.sql`.

## Current Project State

- Backend target is a closed BKV two-wheel charging chain: formal start API, strategy binding, price estimate, paid-order creation, payment-triggered dispatch, identity-channel dispatch, callback settlement, refund/deduction, and order/log query.
- Frontend/admin uses platform auth and `/bkv/*` formal APIs, plus reused legacy management APIs for whitelist, time cards, and charging cards.
- Mini-program uses independent `/xcx/bkv/*` APIs and must get `user_id` from mini-program session instead of trusting request body.
- User-paid mini-program orders should follow: create unpaid BKV order -> `/pay/charging` -> pay success triggers device dispatch through the existing charging payment callback branch.
- Monthly card/time card is implemented on existing `time_card` and `time_card_config`; charging card is `charging_card`; whitelist is `charging_special_list`.
- Mini-program charging-card purchase/recharge/recharge-log independent APIs are not implemented in this round; only card overview/use for BKV start is implemented.

## Current Formal Interface Expectation

- Use `POST /bkv/startCharge` as the formal entry for frontend/admin and Postman tests.
- Keep `POST /bkv/debugStartCharge` only as a development fallback.
- Backend/admin BKV APIs: `/bkv/strategy/list`, `/bkv/station/strategies`, `/bkv/station/strategy/bind`, `/bkv/station/strategy/unbind`, `/bkv/priceEstimate`, `/bkv/startCharge`, `/bkv/order/detail`, `/bkv/order/status`, `/bkv/order/logs`.
- Mini-program BKV APIs: `/xcx/bkv/scanInfo`, `/xcx/bkv/priceEstimate`, `/xcx/bkv/order/create`, `/xcx/bkv/startCharge`, `/xcx/bkv/order/status`, `/xcx/bkv/order/logs`, `/xcx/bkv/stopCharge`, `/xcx/bkv/timeCard/configs`, `/xcx/bkv/timeCard/my`, `/xcx/bkv/timeCard/create`, `/xcx/bkv/timeCard/pay`.
- Reused management/payment APIs: `/pay/charging`, `/charging/special/*`, `/timeCardConfig/*`, `/timeCard/*`, `/pay/timeCard`, `/chargingCard/create`, `/chargingCard/handle`.
- If new helper APIs return `无响应`, verify deployment contains updated `router.js`, `controller/bkvCharging.js`, `controller/xcxBkvCharging.js`, `service/bkvCharging.js`, `service/xcxBkvCharging.js`, `service/bkvIdentity.js`, and payment branch changes.

## Safety With Live Device Tests

- Do not infer a failed device start from `无响应` alone. Check whether an order and a push log were created.
- If an order is still charging but the field device stopped, inspect `/bkv/tradeRecord`, `/bkv/chargeEnd`, protocol `0x1004`, and stop reason fields before manually correcting data.
- For plug removal, map raw stop code `0x2F=08` to a friendly reason such as `plug_removed`; do not leave it as an unexplained fallback like `reason_8`.
- For paid user orders, real original-route refund requires a real payment trade. If no real payment exists, the code should record `pending_refund` or equivalent snapshot/log context rather than silently losing refundable amount.
- When the user asks to modify production DB, be explicit about what is being changed and verify after write.

