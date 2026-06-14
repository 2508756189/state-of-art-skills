# Fengze Flow Validation Reference

## Scope

This reference captures Fengze-specific knowledge established in the thread and is intended to support future chain validation and production troubleshooting.

## Confirmed Fengze assets

- Host: `203.32.85.230`
- Sync lot:
  - `parking_lot_id = efebce10-3dfb-11f1-a131-db270a6c25e6`
  - `parking_lot_no = fznewtest`
  - `auto_pay_level = L2`
- Ports:
  - entry `0ccd2560-3dfc-11f1-a6c9-d1848d225427`, qrcode `0ccd2561`
  - exit `0d2fded0-3dfc-11f1-a932-c9115a25a88e`, qrcode `0d2fded1`
- Devices:
  - entry `eace0f5c-a19a0ceb`
  - exit `2f6d246a-f42fcb90`

## Order mapping

- CPW order number:
  - `cpw_platform.order_list.order_no`
- Main-platform order number:
  - `fz_parking_platform.ipms.order_list.order_no`
- Stable cross-system mapping:
  - `fz_parking_platform.ipms.order_list.out_order_no = cpw_platform.order_list.order_no`

## Scenario evidence rules

### Whitelist

- `order_list.car_type = car_type_white`
- `pay_status = completed`
- `price = 0`
- `paid_fee = 0`
- `message_list.deal_response.open_code = 1`

### Blacklist

- `message_list.deal_response.result_code = BLACK_PLATE_EXIST`
- `message_list.deal_response.open_code = 0`
- `cpw_platform.barrier_log.error_code = BLACK_PLATE_EXIST`

### Monthly card

- `cpw_platform.order_list.parking_card_id1` or `parking_card_id2`
- matching `cpw_platform.parking_card.id`
- `cpw_platform.parking_card.time_type = monthcard1`
- `pay_status = completed`
- `price = 0`
- `paid_fee = 0`
- `message_list.deal_response.open_code = 1`

### No-plate

- Zhenshi direct empty-plate push is not the supported positive path
- supported positive path is QR and mini-program based:
  - `port.qrcode_id`
  - `/barrier/noPlateParking`
  - `/barrier/noPlateAway`
  - `order_list_unlicensed_car`

### Auto-pay

- entry sign-state proof:
  - `sign_level = parking_lot.auto_pay_level`
- readiness proof:
  - `auto_pay.status = enable`
- dynamic closure still requires real sign assets and a usable payment method path

## Known gotcha

Wrong Zhenshi `timeStamp.sec` can cause:

- CPW and main-platform time divergence
- main-platform `AWAY_TIME_ERROR`

Practical rule:

- verify exact Unix seconds in simulation payloads
- clear stale in-park test orders before rerunning the same plate

## Dynamic validation status from this thread

- whitelist: passed
- blacklist: passed
- monthly card: passed
- Zhenshi direct no-plate negative path: confirmed
- QR no-plate positive path: code path confirmed, no live mini-program scan session exercised
- auto-pay: theory confirmed, real closure still blocked by missing live sign assets
