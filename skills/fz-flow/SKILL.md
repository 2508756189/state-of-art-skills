---
name: fz-flow
description: Use when validating or troubleshooting Fengze CPW/main-platform flow logic, especially Zhenshi ingress/egress, whitelist/blacklist/monthly-card behavior, no-plate QR mini-program flow, sync-lot CPW-to-main-platform chaining, auto-pay readiness, and DB evidence for a parking event.
---

# Fz Flow

Use this skill for Fengze flow reasoning and controlled production validation. It is optimized for the real Fengze chain:

`Zhenshi -> barrier_gate_system -> CPW -> parking_platform_service`

Use `production-ops` for generic JumpServer/SFTP/restart mechanics. Use `cpw-production-ops` for Tianyi CPW/main-platform product configuration, permission data, jump-mode deployment conventions, or charging jump-mode context. This skill should stay focused on Fengze business-flow evidence.

For creating or configuring a new Fengze lot, device/lane binding, billing/payment setup, or charging-enabled lot setup, start with `fz-lot-onboarding`; use this skill to verify the resulting entry/exit flow.

## Safety posture

- Treat Fengze production as live. Read first, write only when clearly needed.
- Do not store or repeat database passwords, private keys, cookies, payment credentials, or vendor secrets in skill files.
- Prefer controlled verification with existing assets over ad hoc writes.
- For DB writes, record exact test rows and rollback/disable steps.
- For payment-related work, do not claim real auto-pay is verified unless a real sign asset and real payment method path were exercised.

## Core chain model

Fengze CPW is not a pure passthrough. For sync lots, CPW creates its own order and barrier logs first, then forwards to the main platform.

Use this mental model:

`device -> barrier_gate_system -> CPW local order/barrier state -> optional main-platform sync`

For the same business event:

- CPW order number: `cpw_platform.order_list.order_no`
- main-platform order number: `fz_parking_platform.ipms.order_list.order_no`
- stable cross-system mapping: `fz_parking_platform.ipms.order_list.out_order_no = cpw_platform.order_list.order_no`

## Flow-check workflow

1. Identify which surface you are checking:
   - Zhenshi capture path
   - CPW self-managed path
   - sync-lot forwarding path
   - no-plate QR path
   - auto-pay readiness
2. Confirm route existence in:
   - `barrier_gate_system/routes`
   - `cpw_service/app/router.js`
   - `parking_platform_service/app/router.js`
3. Confirm field mapping and terminal decision fields:
   - `result_code`
   - `open_code`
   - `pay_status`
   - `sign_level`
   - `parking_card_id1/2`
   - `car_type`
4. Confirm which DB tables hold the proof:
   - `order_list`
   - `barrier_log`
   - `parking_card`
   - `special_plate_no`
   - `auto_pay`
   - `order_list_unlicensed_car`
   - `message_list`
5. For sync-lot questions, always map:
   - `main.out_order_no -> cpw.order_no`
6. Separate "theory is complete" from "live asset was exercised".

## Scenario evidence

- Whitelist: prove with `order_list.car_type = car_type_white`, zero price/paid fee, completed payment state, and `open_code = 1`.
- Blacklist: prove with interface-layer `result_code = BLACK_PLATE_EXIST`, `open_code = 0`, and CPW `barrier_log.error_code`.
- Monthly card: prove with `parking_card_id1/2`, matching `parking_card.time_type = monthcard1`, zero settlement, and `open_code = 1`; do not infer it only from `car_type`.
- No-plate: Zhenshi direct empty-plate push is a negative path; supported positive path is QR/mini-program based through `order_list_unlicensed_car`.
- Auto-pay: prove readiness with `auto_pay.status = enable` and entry `sign_level = parking_lot.auto_pay_level`; prove real closure only with a live payment path.

## What to read next

- For structured Fengze facts and validated scenario details, read [references/fengze-flow-validation.md](references/fengze-flow-validation.md).
- For Fengze jump-mode deployment or CPW/main-platform configuration, use `cpw-production-ops` and read [../cpw-production-ops/references/fengze-jump-mode.md](../cpw-production-ops/references/fengze-jump-mode.md).
- For generic server access, SFTP, and restart mechanics, use `production-ops`.
- For SQL inspection, use `postgresql-debug`.

## Verification checklist

- Route exists in the expected service.
- Input fields map cleanly from device payload to CPW/main-platform payload.
- The deciding field for the scenario is identified in the correct table.
- For sync lots, the CPW order and main order are mapped through `out_order_no`.
- Any statement about auto-pay or no-plate positive flow clearly says whether it was code-confirmed only or dynamically exercised.
