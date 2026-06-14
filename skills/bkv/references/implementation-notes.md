# BKV Implementation Notes

## Platform/Middleware Coupling

Any BKV change in `parking_platform_service` may require a matching check or change in the `barrier_system` middleware. Do not assume platform-only changes are enough.

Check middleware when changing:

- Charge mode translation.
- BKV protocol field composition.
- Start/stop command payload shape.
- Callback URL names and callback body shape.
- Raw frame parsing and friendly protocol labels.
- Message log persistence into `fz_parking_platform_log`.
- Timeout, retry, and "request sent, waiting for device response" behavior.

## Strategy Semantics

### Duration

- Request mode: `charge_mode=duration`.
- Input: `charge_time_min`.
- Device command should carry time mode and requested minutes, normally `0x12=01` plus duration minutes field such as `0x14`.
- Billing: after charge end, calculate actual elapsed minutes, round up to hours, and multiply by `hour_price`.
- Full self-stop is treated by the agreed business rule as 10 hours if applicable.
- If prepaid, refund unused amount via original route when payment integration supports it.

### Electricity-Service

- Request mode: `charge_mode=electricity_service`.
- Input: `energy_kwh`.
- Strategy options hold `electric_price` and `service_price`.
- Device command should carry energy mode and requested kWh, normally `0x12=02` plus energy field such as `0x15`.
- Billing: `actual_kwh * (electric_price + service_price)`.
- Less than `0.1` kWh is billed as `0.1` kWh.
- Do not implement BKV service-fee ladder protocol fields in this round unless the user reopens that scope.

### Per-Use

- Request mode: `charge_mode=per_use`.
- Input: `total_amount_cent`.
- Match `total_amount_cent / 100` against `per_use_options.amount`.
- Use the matched option's `duration_min` as the actual duration to send.
- Per-use dispatch should use duration-mode behavior, not a separate "amount + time limit" interpretation unless the protocol requirement changes.
- Default business decision in this thread: early end does not refund for per-use.

## Billing And Refund

- Normal paid mini-program orders should be created unpaid first, paid through `/pay/charging`, then dispatched after payment success.
- Duration prepaid orders: final fee is actual billed hours times `hour_price`; refundable amount is paid amount minus final fee.
- Electricity-service prepaid orders: final fee is billed kWh times `electric_price + service_price`; refundable amount is paid amount minus final fee.
- Per-use orders: final fee is the selected fixed option amount; early end does not produce a normal refund.
- If there is no real payment trade, do not pretend an original-route refund succeeded. Record pending refund state and context in snapshot/logs.
- Keep `ChargingOrder.price`, `electric_price`, `service_price`, `price_arr`, `billing_status`, `snapshot.bkv_charge_profile`, `snapshot.bkv_trade_record`, and settlement logs consistent.

## Identity Channels

Normal user, monthly card, charging card, and whitelist should use the same BKV preparation/settlement concepts, but not necessarily the same HTTP entry.

- `user`: normal user payment and settlement. Mini-program should use order create -> `/pay/charging` -> pay success dispatch.
- `monthly_card`: validate two-wheel time-card minute balance by user id; lock/deduct actual minutes; keep unused minutes. Backed by `time_card` and `time_card_config`.
- `charging_card`: validate `charging_card_no`, settle against card balance, create card/balance logs. Backed by `charging_card` and `charging_card_log`.
- `whitelist`: validate user qualification by mobile/user context in `charging_special_list`; user-facing amount can be zero while retaining internal order context.

Store identity validation and settlement results in `ChargingOrder.snapshot.bkv_identity_context` and `snapshot.bkv_identity_settlement` rather than adding ordinary fields unless safe reuse is impossible.

## Frontend And Mini-Program Boundary

- Backend/admin uses `/bkv/*` and the existing platform auth/resource system.
- Mini-program uses `/xcx/bkv/*`; do not rely on frontend-submitted `user_id` when a session user is available.
- Reused old APIs only need BKV field notes in docs: `/pay/charging`, `/charging/special/*`, `/timeCardConfig/*`, `/timeCard/*`, `/pay/timeCard`, `/chargingCard/*`.
- New BKV and `/xcx/bkv/timeCard/*` APIs should have complete request/response documentation for frontend handoff.
- Charging card purchase/recharge in mini-program remains a known gap; current implementation supports query overview through scan/start context and using an existing card for charging.

## Friendly Protocol Names

Use user-friendly names in logs and APIs:

- `0x1001`: BKV device heartbeat or start/ACK-related device report, depending on middleware interpretation.
- `0x1002`: BKV realtime/status upload.
- `0x1004`: BKV trade/finish record.
- `0x2F=08`: `plug_removed`.

Do not leave field operators with raw-only labels such as `BKV设备上行报文-0x1002` if a friendlier summary is available.

## Known Failure Signatures

### `无响应` on `/bkv/startCharge`

Likely route miss/stale deployment if:

- HTTP response arrives in about 1 ms.
- No `charging_order` exists.
- No `charging_push_log` exists.
- `request_log_YYYYMMDD` shows URL `/bkv/startCharge` with response `无响应`.

Check deployed code and actual restarted process.

### Device stopped but order remains charging

Likely callback/settlement link issue if:

- Field staff confirm device stopped.
- Device heartbeat still arrives.
- Order status remains charging.

Inspect middleware `/bkv/messageLog`, protocol `0x1004`, platform `/bkv/tradeRecord`, platform `/bkv/chargeEnd`, and order update errors.

### Price fields empty

Check whether settlement ran through `tradeRecord`/`chargeEnd`, whether final breakdown selected the right strategy, and whether final update writes `price`, `electric_price`, `service_price`, `price_arr`, `billing_status`, and `snapshot.bkv_trade_record`.

### Whitelist or time-card not visible in UI

Check that data was written to the existing UI-backed tables:

- Whitelist should be in `ipms.charging_special_list` and match the UI's type/mobile/data-owner filters.
- Time card should be in `ipms.time_card` with a matching `ipms.time_card_config`; two-wheel/BKV distinction should use config `options`.
- Charging card should be in `ipms.charging_card`.

## Known Remaining Scope

- Backend BKV main chain is intended to be functionally complete, but payment/refund and live-device behavior still need production-like regression.
- Frontend/admin UI and mini-program UI are not implemented here; only backend/API contracts and docs are prepared.
- Mini-program charging-card purchase/recharge/recharge-log APIs are not implemented.
- BKV service-fee ladder protocol fields and power-mode charging remain optional future scope unless business asks for them.
