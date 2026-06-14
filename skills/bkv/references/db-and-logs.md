# BKV Database And Logs

Use `psql` against the user-provided PostgreSQL host and credentials when the user explicitly asks to inspect or modify live data. Business tables are in `fz_parking_platform.ipms`; request/message logs are in `fz_parking_platform_log`.

Do not expose credentials in summaries. Use them only for explicit live DB tasks.

## Common Tables

- `ipms.charging_order`: order state, price fields, snapshot.
- `ipms.charging_port`: port enable/free/charging state.
- `ipms.charging_pile`: pile/device number and online/status metadata.
- `ipms.charging_station`: station options and strategy mapping.
- `ipms.charging_strategy`: strategy options JSON.
- `ipms.charging_push_log`: platform-side charging push and callback logs.
- `ipms.trade_record`: final trade/settlement records.
- `ipms.charging_special_list`: charging whitelist and special user records; BKV whitelist should be visible to existing UI if filters match.
- `ipms.time_card_config`: time-card/month-card package config; BKV two-wheel packages should be marked in `options`, for example `vehicle_type='two_wheel'` or `bkv_enabled=true`.
- `ipms.time_card`: user time-card records and remaining/used duration.
- `ipms.charging_card`: charging card master data, balance, binding user.
- `ipms.charging_card_log`: charging card balance/deduction logs, if present in the deployed schema.
- `fz_parking_platform_log.request_log_YYYYMMDD`: HTTP request and middleware message logs.
- `ipms.base_resource`: API resource/permission registration.

## Order Checks

```sql
select id, order_no, pile_no, port_no, status, billing_status, price,
       electric_price, service_price, charging_power, created_at, updated_at,
       snapshot
from ipms.charging_order
where order_no = 'REAL-DUR-0522-01';
```

If column names differ, discover columns first:

```sql
select column_name
from information_schema.columns
where table_schema = 'ipms'
  and table_name = 'charging_order'
order by ordinal_position;
```

## Push Log Checks

```sql
select created_at, order_no, pile_no, port_no, content, request_content, response_content
from ipms.charging_push_log
where order_no = 'REAL-DUR-0522-01'
order by created_at desc;
```

If no push log exists after `/bkv/startCharge`, the request likely did not enter order dispatch.

## Request Log Checks

```sql
select request_time, url, request_param, response, cost_time
from request_log_20260522
where url in ('/bkv/startCharge', '/bkv/debugStartCharge', '/bkv/priceEstimate')
order by request_time desc
limit 20;
```

Interpretation:

- `response={"success":false,"error":"无响应"}` with `cost_time` near `00:00:00.001` usually means route miss or no controller body, not device timeout.
- `pileHeartbeatPack` returning `{"success":true,"data":"接收成功"}` proves BKV callback route is alive.
- `/bkv/messageLog` rows may have `response=无响应` because message logging route records payloads but may not return a business body; inspect its `request_param`.

## Message Log Query

```sql
select request_time, request_param
from request_log_20260522
where url = '/bkv/messageLog'
  and request_param::text like '%REAL-DUR-0522-01%'
order by request_time desc;
```

For device-level diagnosis, search by device, protocol, or trade/order number:

```sql
select request_time, request_param
from request_log_20260522
where url = '/bkv/messageLog'
  and request_param::text like '%1009025121600144%'
  and request_param::text like '%0x1004%'
order by request_time desc
limit 20;
```

## Resource Checks

Backend/admin BKV resources:

```sql
select id, name, url, guest_access, status, deleted
from ipms.base_resource
where url in (
  '/bkv/startCharge',
  '/bkv/strategy/list',
  '/bkv/station/strategies',
  '/bkv/station/strategy/bind',
  '/bkv/station/strategy/unbind',
  '/bkv/priceEstimate',
  '/bkv/order/detail',
  '/bkv/order/status',
  '/bkv/order/logs'
)
order by url;
```

Mini-program BKV resources:

```sql
select id, name, url, guest_access, status, deleted
from ipms.base_resource
where url in (
  '/xcx/bkv/scanInfo',
  '/xcx/bkv/priceEstimate',
  '/xcx/bkv/order/create',
  '/xcx/bkv/startCharge',
  '/xcx/bkv/order/status',
  '/xcx/bkv/order/logs',
  '/xcx/bkv/stopCharge',
  '/xcx/bkv/timeCard/configs',
  '/xcx/bkv/timeCard/my',
  '/xcx/bkv/timeCard/create',
  '/xcx/bkv/timeCard/pay'
)
order by url;
```

Resource rows are necessary for permission/menu config but do not prove the Node process loaded the route.

## Strategy Config Checks

```sql
select id, name, type, options
from ipms.charging_strategy
where deleted = false
  and options::text like '%charge_type%';
```

```sql
select id, name, options
from ipms.charging_station
where name like '%丰泽%'
  and options::text like '%charging_strategy_ids%';
```

## Whitelist Checks

```sql
select id, mobile, type, is_free, unlimited, charging_station_ids, data_owner_id, deleted, options
from ipms.charging_special_list
where deleted = false
  and mobile = 'TEST_MOBILE';
```

If UI does not show a test whitelist, compare the UI request filters with `mobile`, `type`, `data_owner_id`, `deleted`, station binding, and permission scope.

## Time-Card Checks

```sql
select id, name, type, price, duration, options, deleted
from ipms.time_card_config
where deleted = false
  and options::text like '%two_wheel%';
```

```sql
select id, user_id, mobile, config_id, status, total_duration, remain_duration,
       start_time, end_time, options, deleted
from ipms.time_card
where deleted = false
  and user_id = 'TEST_BKV_USER_001'
order by created_at desc;
```

If column names differ, discover `time_card` and `time_card_config` columns from `information_schema.columns`.

## Charging-Card Checks

```sql
select id, card_no, denomination, balance, bind_user_id, mobile, status, data_owner_id, deleted
from ipms.charging_card
where deleted = false
  and card_no = 'TEST_BKV_CARD_001';
```

```sql
select *
from ipms.charging_card_log
where card_no = 'TEST_BKV_CARD_001'
order by created_at desc
limit 20;
```

If `charging_card_log` differs or does not exist, discover charging-card related tables:

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = 'ipms'
  and table_name like '%charging%card%';
```

## Deployment-Version Diagnosis

If a newly added endpoint returns `无响应`:

1. Confirm `request_log_YYYYMMDD` has the request and `cost_time` is near 1 ms.
2. Confirm no `charging_order` was created.
3. Confirm no `charging_push_log` was created.
4. Test a known callback route like `/bkv/pileHeartbeatPack` with `{}` and expect a validation error rather than route miss.
5. Compare deployed files with local `router.js`, `controller/bkvCharging.js`, `controller/xcxBkvCharging.js`, `service/bkvCharging.js`, `service/xcxBkvCharging.js`, `service/bkvIdentity.js`, and payment service changes.
6. Confirm the process restarted is the one behind `60000/parking/service`.

## Log Design Expectation

For every BKV charging flow, retain enough DB logs to reconstruct:

- Platform start request.
- Platform-to-middleware/device command.
- Raw device frame, if available.
- Parsed protocol command and friendly name.
- Platform callback route and response.
- Order status update.
- Trade record and settlement result.
- Stop reason, including `plug_removed`.
- Payment, refund, monthly-card deduction, charging-card deduction, or whitelist settlement result.
