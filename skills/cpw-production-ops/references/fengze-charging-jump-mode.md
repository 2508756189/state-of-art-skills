# Fengze Charging Jump Mode

## Scope

Use this reference when Fengze charging work intersects CPW jump mode, main platform configuration, BKV two-wheel middleware, or TLD four-wheel integration.

## Core rule

Fengze uses CPW jump mode like Ganzi:

- CPW remains the barrier/cloud-duty jump surface.
- Charging business is handled by `parking_platform_service`.
- Charging business data belongs in `fz_parking_platform.ipms`.
- Do not create charging station, pile, port, order, or vendor records in CPW logical databases for this mode.

## Production services

- `parking_platform_service`
  - role: main platform charging business, routes, orders, station/pile/port data
  - local port: `60061`
  - path: `/data/projects/parking_platform_service`
- `barrier_gate_system`
  - role: barrier middleware plus BKV TCP charging middleware
  - HTTP port: `60072`
  - BKV TCP port: `60073`
  - path: `/data/projects/barrier_gate_system`
- `cpw_service`
  - role: CPW barrier/cloud-duty jump behavior
  - not the charging business owner

Use `production-ops` for exact server access, upload, backup, restart, and port verification commands.

## Four-wheel TLD

TLD four-wheel charging is a main-platform integration.

Important configuration:

- `parking_platform_service/config/build/appConfig/prod-fz/url.js`
  - `charging.tld`
  - `tldUrl`
- `parking_platform_service/config/build/appConfig/prod-fz/charging.js`
  - TLD message key, IV, operator secret, signature secret
  - Prefer environment variables or deployment configuration; do not commit vendor secrets.

Known Fengze备案 facts:

- company: `中国电信股份有限公司福州分公司`
- operator id: `589559607`
- callback base from the备案 sheet: `https://fengzecj.genchuan.cn:60000/parking/service/hlht/v1.0`
- city/scope: `泉州市`
- contact details may exist in local docs, but do not repeat private contact or secret values in final summaries unless the user explicitly needs them.

Recommended prepay callback route for clear internal routing:

- `/parking/service/tld/notification_trade_result`
- `/parking/service/tld/notification_refund_result`

The `/hlht/v1.0/*` compatibility route is behind legacy HLHT auth/middleware. Verify the exact vendor signing/encryption path before telling TLD to use the HLHT alias.

## Two-wheel BKV

BKV two-wheel charging uses:

`BKV device TCP -> barrier_gate_system -> parking_platform_service /bkv/* -> fz_parking_platform.ipms`

Main platform callback routes include:

- `/bkv/pileAuth`
- `/bkv/pileHeartbeatPack`
- `/bkv/uploadRealTimeMonitoringData`
- `/bkv/remoteStartChargeResponse`
- `/bkv/remoteEndChargeResponse`
- `/bkv/tradeRecord`
- `/bkv/chargeEnd`
- `/bkv/nfcStartCharge`
- `/bkv/nfcEndCharge`
- `/bkv/eventUpload`
- `/bkv/timeSynchronizationResponse`
- `/bkv/remoteCommandResponse`

Middleware command routes include:

- `/bkv/remotecontrolboot`
- `/bkv/remotecontrolend`
- `/bkv/timesynchronization`
- `/bkv/querypileinfo`
- `/bkv/systemparamset`
- `/bkv/systemparamquery`
- `/bkv/thresholdset`
- `/bkv/thresholdquery`
- `/bkv/upgrade`

Production config expectations:

- main platform `chargingDeviceUrl -> http://127.0.0.1:60072`
- barrier middleware `url.bkv_platform -> http://127.0.0.1:60061`
- keep `barrier_gate_system config.url.main` for CPW/barrier jump behavior; do not repoint the whole value to main platform just for BKV.

## 联调 seed data from this thread

The following simulated records were created for Fengze joint testing:

- data owner: `16ecaed0-3a0a-11f1-be0e-2515f5bfb5ff` (`泉州丰泽`)
- parking lot: `efebce10-3dfb-11f1-a131-db270a6c25e6` (`丰泽测试联调车场`)
- TLD four-wheel simulated station:
  - station no: `FZ-TLD-SIM-001`
  - station id: `fztld-station-sim-20260430`
  - pile no: `589559607FZTLDPILE01`
  - connector id: `589559607FZTLD0101`
- BKV two-wheel simulated station:
  - station no: `FZ-BKV-SIM-001`
  - station id: `fzbkv-station-sim-20260430`
  - pile no: `BKVTEST0001`
  - ports: `BKVTEST000101` through `BKVTEST000104`
- `allow_charging_fee` for the Fengze data owner:
  - `min_fee = 0.5`

Rollback SQL was generated locally in the project workspace at:

`甘孜cpw跳板接主平台项目/tmp/fz_charging_seed_rollback_20260430.sql`

Do not assume this rollback file exists on every machine; if missing, reconstruct rollback from the explicit IDs above.
