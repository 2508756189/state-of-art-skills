# BKV Project Context

## Workspace

- Main workspace: use the active Fengze workspace from the user. On this machine, the common workspace is `D:/电动车充电对接文档/甘孜cpw跳板接主平台项目`; the older `C:/Users/mm/Desktop/丰泽` path may belong to another machine.
- Platform service: `parking_platform_service`.
- Middleware to check together with platform changes: `barrier_system` or similarly named barrier-gate middleware project in the workspace.
- Main documentation folder: `二轮充电文档`.

## Platform Files Changed In This Thread

- `parking_platform_service/app/router.js`: BKV backend/admin routes, mini-program `/xcx/bkv/*` routes, reused route registration checks.
- `parking_platform_service/app/controller/bkvCharging.js`: backend/admin BKV controller methods for start, strategy, estimate, order, status, and logs.
- `parking_platform_service/app/controller/xcxBkvCharging.js`: mini-program BKV controller methods for scan, estimate, order creation, start, status, logs, stop, and time-card APIs.
- `parking_platform_service/app/service/bkvCharging.js`: shared formal start flow, billing settlement, helper APIs, order-log aggregation, strategy binding, BKV profile/breakdown logic.
- `parking_platform_service/app/service/xcxBkvCharging.js`: mini-program scan/estimate/order/start/status/log/time-card flow and user-session handling.
- `parking_platform_service/app/service/bkvIdentity.js`: monthly-card, charging-card, whitelist identity channel logic and settlement snapshots.
- `parking_platform_service/app/service/charging.js`: BKV identity preparation before charging order creation.
- `parking_platform_service/app/service/chargingOrder.js`: snapshot identity context persistence.
- `parking_platform_service/app/service/pay.js` or related payment service: BKV charging order branch so `/pay/charging` can trigger dispatch after payment success.

## Documentation/Postman Files

- `二轮充电文档/BKV真实设备测试操作手册.md`: true-device operation, log checks, callback chain, troubleshooting.
- `二轮充电文档/BKV真实设备测试.postman_collection.json`: Postman collection used for real-device and identity-channel tests.
- `二轮充电文档/BKV真实设备测试.postman_environment.json`: Postman environment when an environment-based collection is needed.
- `二轮充电文档/BKV下一轮正式接口说明.md`: earlier formal API planning notes.
- `二轮充电文档/BKV前端小程序接口说明.md`: current handoff document for frontend/admin and mini-program teams.
- `二轮充电文档/BKV正式接口权限资源SQL.sql`: route/resource SQL, including backend/admin and mini-program BKV routes where applicable.
- `二轮充电文档/PLAN.md`: development planning notes.

## Database

- Business DB: `fz_parking_platform`.
- Business schema: `ipms`.
- Request/log DB: `fz_parking_platform_log`.
- Credentials were provided by the user in the conversation. Do not expose them in broad summaries; use them only when live DB work is explicitly needed.

## Known Data

- Real platform base URL observed in code/config: `https://fengzecj.genchuan.cn:60000/parking/service`.
- Middleware device URL pattern observed in config: `chargingDeviceUrl = http://127.0.0.1:60072`.
- Real BKV pile used in field tests: `1009025121600144`.
- Real BKV HTTP port number for physical port 0: send `"00"`.
- Simulated pile: `BKVTEST0001`.
- Simulated station id used earlier: `fzbkv-station-sim-20260430`.

## Strategy Config Shape

Station `options` should contain `charging_strategy_ids`:

```json
{
  "charging_strategy_ids": {
    "duration": "duration-strategy-id",
    "electricity_service": "electricity-strategy-id",
    "per_use": "per-use-strategy-id"
  }
}
```

Typical `ChargingStrategy.options`:

```json
{ "charge_type": "duration", "hour_price": 1.2, "default_charge_time_min": 10 }
```

```json
{ "charge_type": "electricity_service", "electric_price": 0.5, "service_price": 0.3, "max_charge_time_min": 10 }
```

```json
{
  "charge_type": "per_use",
  "per_use_options": [
    { "amount": 2, "duration_min": 10 },
    { "amount": 3, "duration_min": 10 }
  ]
}
```

## Backend/Admin Interface State

- Formal start: `POST /bkv/startCharge`.
- Development fallback: `POST /bkv/debugStartCharge`.
- Strategy and station: `POST /bkv/strategy/list`, `POST /bkv/station/strategies`, `POST /bkv/station/strategy/bind`, `POST /bkv/station/strategy/unbind`.
- Estimate and order: `POST /bkv/priceEstimate`, `POST /bkv/order/detail`, `POST /bkv/order/status`, `POST /bkv/order/logs`.
- Reused whitelist management: `/charging/special/*`, especially user whitelist by mobile in `charging_special_list`.
- Reused time-card/month-card management: `/timeCardConfig/*`, `/timeCard/*`, `/pay/timeCard`, backed by `time_card_config` and `time_card`.
- Reused charging-card management: `/chargingCard/create`, `/chargingCard/handle`, backed by `charging_card` and `charging_card_log`.

## Mini-Program Interface State

- `POST /xcx/bkv/scanInfo`: scan page station/pile/port/strategy/rights overview.
- `POST /xcx/bkv/priceEstimate`: strategy estimate for user/monthly-card/charging-card/whitelist scenarios.
- `POST /xcx/bkv/order/create`: create unpaid user-paid BKV charging order.
- `POST /pay/charging`: reused payment API; after successful payment, dispatches BKV device for the paid order.
- `POST /xcx/bkv/startCharge`: direct dispatch for no-external-payment identity channels such as monthly card, charging card, and whitelist.
- `POST /xcx/bkv/order/status`, `POST /xcx/bkv/order/logs`, `POST /xcx/bkv/stopCharge`: order polling, user-friendly logs, and user stop.
- `POST /xcx/bkv/timeCard/configs`, `/my`, `/create`, `/pay`: BKV two-wheel time-card purchase/query/payment flow.
- Not implemented: mini-program independent charging-card purchase, recharge, and recharge-log APIs such as `/xcx/bkv/chargingCard/*`.

## Deployment Consistency Checklist

When production returns `无响应` for new BKV APIs, compare deployed files with local versions:

- `parking_platform_service/app/router.js`.
- `parking_platform_service/app/controller/bkvCharging.js`.
- `parking_platform_service/app/controller/xcxBkvCharging.js`.
- `parking_platform_service/app/service/bkvCharging.js`.
- `parking_platform_service/app/service/xcxBkvCharging.js`.
- `parking_platform_service/app/service/bkvIdentity.js`.
- `parking_platform_service/app/service/charging.js`.
- `parking_platform_service/app/service/chargingOrder.js`.
- `parking_platform_service/app/service/pay.js` or the current payment callback service that handles `/pay/charging`.

Also confirm the restarted process is the one actually serving `https://fengzecj.genchuan.cn:60000/parking/service`.

## Middleware Coupling Checklist

Whenever changing `parking_platform_service` BKV code, inspect the corresponding `barrier_system` middleware code for:

- Remote-start command payload fields and protocol code mapping.
- Charge mode values sent to the device, especially `0x12`, `0x14`, `0x15`, amount, duration, and energy fields.
- Device packet parsing for `0x1001`, `0x1002`, `0x1004`, and stop reason `0x2F`.
- Callback route names sent back to the platform, such as `/bkv/remoteStartChargeResponse`, `/bkv/uploadRealTimeMonitoringData`, `/bkv/tradeRecord`, and `/bkv/chargeEnd`.
- Logging of raw frames, parsed payload, platform callback response, order number, port number, trade number, and protocol command.
- Timeout and retry behavior when the platform or device does not respond.
