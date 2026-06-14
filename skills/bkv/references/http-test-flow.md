# BKV HTTP And Field-Test Flow

## Formal Backend/Admin Entry

Use the formal API for backend/admin and Postman testing:

```http
POST {{baseUrl}}/bkv/startCharge
Content-Type: application/json
```

Keep `/bkv/debugStartCharge` as development fallback only.

## Duration Charging

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "logic_card_no": "BKV_DEBUG",
  "real_card_no": "BKV_DEBUG",
  "balance": "0",
  "pay_type": "pay_after",
  "charge_mode": "duration",
  "charge_time_min": 10,
  "identity_source": "user",
  "order_no": "REAL-DUR-YYYYMMDD-01"
}
```

Expected device command meaning: duration strategy, send BKV duration mode and duration minutes.

## Electricity-Service Charging

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "logic_card_no": "BKV_DEBUG",
  "real_card_no": "BKV_DEBUG",
  "balance": "0",
  "pay_type": "pay_after",
  "charge_mode": "electricity_service",
  "energy_kwh": 0.1,
  "identity_source": "user",
  "order_no": "REAL-ENE-YYYYMMDD-01"
}
```

Billing expectation: actual kWh multiplied by `electric_price + service_price`, with less than `0.1` kWh charged as `0.1` kWh.

## Per-Use Charging

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "logic_card_no": "BKV_DEBUG",
  "real_card_no": "BKV_DEBUG",
  "balance": "0",
  "pay_type": "pay_after",
  "charge_mode": "per_use",
  "total_amount_cent": 200,
  "identity_source": "user",
  "order_no": "REAL-USE-YYYYMMDD-01"
}
```

Per-use should match `total_amount_cent / 100` to `per_use_options.amount`, then use that option's `duration_min`. It is not a separate BKV amount-plus-limit mode unless protocol requirements change.

## Identity Channel Direct Starts

Use `/bkv/startCharge` for backend/admin direct tests, or `/xcx/bkv/startCharge` for mini-program direct starts that do not need external payment:

### Monthly Card

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "user_id": "TEST_BKV_USER_001",
  "identity_source": "monthly_card",
  "charge_mode": "duration",
  "charge_time_min": 10,
  "order_no": "REAL-MON-YYYYMMDD-01"
}
```

Expected: validate usable two-wheel time-card minutes, start device, and deduct actual minutes after charge end.

### Charging Card

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "user_id": "TEST_BKV_USER_001",
  "identity_source": "charging_card",
  "charging_card_no": "TEST_BKV_CARD_001",
  "charge_mode": "duration",
  "charge_time_min": 10,
  "order_no": "REAL-CARD-YYYYMMDD-01"
}
```

Expected: validate existing `charging_card` balance, start device, and deduct final payable amount once.

### Whitelist

```json
{
  "pile_no": "1009025121600144",
  "port_no": "00",
  "user_id": "TEST_BKV_USER_001",
  "identity_source": "whitelist",
  "charge_mode": "duration",
  "charge_time_min": 10,
  "order_no": "REAL-WHITE-YYYYMMDD-01"
}
```

Expected: validate `charging_special_list` whitelist qualification, start device, and settle user-facing amount as zero.

## Mini-Program Paid User Flow

For normal paid users, do not directly dispatch before payment:

1. `POST /xcx/bkv/scanInfo`: show station, port status, strategies, and user rights.
2. `POST /xcx/bkv/priceEstimate`: preview fee for `duration`, `electricity_service`, or `per_use`.
3. `POST /xcx/bkv/order/create`: create unpaid BKV charging order and snapshot the selected BKV profile.
4. `POST /pay/charging`: complete the existing charging payment flow.
5. Payment success branch dispatches BKV device.
6. `POST /xcx/bkv/order/status`: poll order/payment/charging/refund status.
7. `POST /xcx/bkv/order/logs`: show user-friendly timeline.
8. `POST /xcx/bkv/stopCharge`: user-requested early stop, with final settlement based on device end packet.

## Mini-Program Time-Card Flow

Use existing time-card business tables through BKV mini-program wrappers:

1. `POST /xcx/bkv/timeCard/configs`: list buyable two-wheel/BKV time-card packages.
2. `POST /xcx/bkv/timeCard/create`: create a pending time-card order without forcing a license plate for two-wheel.
3. `POST /xcx/bkv/timeCard/pay`: reuse existing time-card payment flow.
4. `POST /xcx/bkv/timeCard/my`: show current usable time-card total, remaining minutes, validity, and status.
5. `POST /xcx/bkv/startCharge` with `identity_source=monthly_card`: use time-card minutes for charging.

## Expected Callback Chain

For a real device, do not manually call callbacks unless simulating device behavior. The middleware/device chain should call the platform:

1. `/bkv/remoteStartChargeResponse`: device accepted or rejected remote start.
2. `/bkv/uploadRealTimeMonitoringData`: charging/idle/realtime status, often mapped from `0x1002`.
3. `/bkv/tradeRecord`: transaction/settlement record, often mapped from `0x1004`.
4. `/bkv/chargeEnd`: final charge-end notification.

## Field Operation Checklist

Before start:

- Confirm pile is online via heartbeat logs.
- Confirm target port is `enable` and `free`.
- Confirm station options map the selected strategy id.
- Confirm selected `ChargingStrategy.options` has the expected price and duration/energy config.
- Confirm no unfinished previous order occupies the same port.
- For paid mini-program tests, confirm a real payment trade exists if original-route refund must be tested.

After start API returns:

- A true platform dispatch should create `charging_order`.
- It should also create at least one `charging_push_log` or middleware message log depending on the chain.
- If the response is `请求发送成功，等待设备响应，请稍后刷新`, wait for ACK/logs.
- If response is `无响应` in about 1 ms and no order exists, treat as route/deployment issue.

After device starts:

- Check `remoteStartChargeResponse` or corresponding message log for ACK.
- Check `uploadRealTimeMonitoringData` or `0x1002` status frames.
- Check order status transitions.

After device stops:

- Check `tradeRecord` or `0x1004`.
- Check `chargeEnd`.
- Check order status becomes `finish`.
- Check port returns `free`.
- Check fee fields, snapshot, trade record, refund/deduction result.

## True Device Test Notes

- Field staff may confirm charging starts even when platform logs are incomplete; this means dispatch reached the middleware/device, not necessarily that callbacks settled correctly.
- For plug removal tests, expect a stop reason in the device finish packet. Map `0x2F=08` to `plug_removed`.
- If device stops but order remains charging, inspect middleware message logs and platform callback logs before manual correction.
- If frontend shows the charging gun status time as stale, inspect latest `0x1002` or heartbeat/status update logs before assuming the port is truly stale.
