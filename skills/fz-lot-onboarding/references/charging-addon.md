# Charging Add-On

Use this when a new or existing parking lot needs two-wheel or four-wheel charging support, especially when parking-fee waiver is part of the business.

## Ownership Rule

In Fengze jump mode, charging business data is in `fz_parking_platform.ipms`. Do not create charging stations, piles, ports, orders, or vendor rows in CPW logical DBs unless a current code path proves CPW owns that charging feature.

## Four-Wheel Charging Checklist

Verify:

- company/vendor record and `out_post_style` match the intended provider
- station, pile, and port records have the right `data_owner_id`
- charging station maps to the intended `parking_lot_id`
- pile and port ids/nos match vendor connector ids
- connector status is interpreted from the vendor or HLHT spec, not guessed
- local payment method: `ums_pay` or configured method is available
- TLD/HLHT path: prepay, start, stop, final order, refund are understood before a paid test

## Parking-Fee Waiver

Required facts:

- charging order finishes successfully: `charging_order.status='finish'`
- charging payment is completed: `pay_status='completed'`
- charging order links to parking order by `rela_order_id` or `rela_order_no`, or at least same `parking_lot_id`, `plate_no`, and `plate_no_color`
- `charging_order.parking_lot_id` is populated
- `base_config.key='charging_bonus'` contains the lot id under `value.value`

Example config:

```json
{
  "value": {
    "<parking_lot_id>": { "range": "hour", "num": 720 }
  }
}
```

Use `{ "range": "all" }` only for true full waiver.

## Verification

For a controlled test:

1. Create or identify a parking order in `parking/uncleared`.
2. Ensure a related charging order is `finish/completed`.
3. Call or observe `/barrier/beforeAway` with `allowance=0`.
4. Expected response for a small unpaid parking fee: `price=0`.
5. Verify `barrier_log.data.charging_bonus` contains the charging order number and allowance.
6. Verify final parking order is `away/completed`.

Pitfall: proactive barrier coupon delivery can fail if `/crypto/barrier/UpTicketNo` is absent. The main-platform `beforeAway` fallback is the critical safety net.

## Local UMS Charging Refund

When four-wheel charging uses local platform collection:

- `refund_list.method='ums_pay'` should be submitted by `app/schedule/refund.js`
- the `ums_pay` switch branch must not fall through to `card_pay`
- `processing` rows are not picked again by the scheduler
- recovery for exact stuck rows: prove no channel success, set back to `waiting`, then verify UMS success result fields

Use `fz-hlht-charging-ops` for detailed charging-order/refund triage.
