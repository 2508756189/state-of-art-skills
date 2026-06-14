# HLHT Status Reference

Use this reference when interpreting `query_station_status`, `notification_stationStatus`, and connector records.

## Connector `Status`

HLHT/T/CEC connector status:

| Value | Meaning |
| --- | --- |
| `0` | 离网 |
| `1` | 空闲 |
| `2` | 占用（未充电） |
| `3` | 占用（充电中） |
| `4` | 占用（预约锁定） |
| `255` | 故障 |
| `999` | 自定义 |

Operational interpretation:

- `Status=2` is not a failure by itself. It can mean the vehicle/gun is connected but charging has not started.
- `Status=1` is not the only candidate for testing; a real start flow often requires the gun to be inserted first, which may appear as `Status=2`.
- `Status=3` means a charging session is already active; do not start a new order without identifying the active session.
- `Status=0` and `Status=255` are not suitable for a normal start test.

## `ParkStatus`

| Value | Meaning |
| --- | --- |
| `0` | 未知 |
| `10` | 空闲 |
| `50` | 占用 |

Do not treat `ParkStatus=0` as empty, normal, or abnormal. It only means unknown.

## `LockStatus`

| Value | Meaning |
| --- | --- |
| `0` | 未知 |
| `10` | 已解锁 |
| `50` | 已上锁 |

Do not treat `LockStatus=0` as unlocked or normal. It only means unknown.

## Platform Mapping Caution

Fengze code has mapped HLHT `Status=2` to local `charging_port.using_status='occupy'`. That is acceptable as a local physical state, but it must not be used as proof that:

- a platform charging order is active;
- the connector cannot be started;
- the previous failed order caused the connector state.

For order-state conclusions, correlate:

- `StartChargeSeqStat`
- `notification_start_charge_result`
- `notification_equip_charge_status`
- final `notification_charge_order_info`
- local `charging_order.status`, `charging_time`, and `finish_time`

## Common Correct Statements

- “`Status=2` means occupied but not charging; it may be a plugged-in pre-start state.”
- “`LockStatus=0` and `ParkStatus=0` are unknown; they do not prove the lock/space is normal.”
- “The platform has no stuck charging order if `charging_order.status != 'finish'` returns zero rows, even if TLD reports `Status=2`.”
- “Start failure must be diagnosed from TLD start result and `FailReason`, not from `Status=2` alone.”
