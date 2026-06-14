# Fengze Lot Standard Flow

Use this as the main checklist for a new Fengze parking lot or an existing lot that needs to be brought under AI-managed configuration.

## Phase 1: Scope And Topology

Determine:

- business owner/data owner
- main platform lot vs CPW jump lot vs both
- device vendor and middleware path
- entry lanes, exit lanes, mixed lanes
- payment methods and merchant ownership
- charging support: none, two-wheel, four-wheel, or both
- reference lot, if any

For Fengze jump mode:

- CPW handles barrier/cloud-duty jump behavior.
- Main `parking_platform_service` owns main parking business.
- Charging business data belongs in `fz_parking_platform.ipms`, not CPW logical DBs.

## Phase 2: Lot Base Data

Verify or create only after diffing:

- `parking_lot`: id, name, `parking_lot_no`, `logic_type`, `data_owner_id`, status, interface config, payment/auto-pay settings
- parking zones and spaces if the product uses them for reports or device mapping
- billing strategy and strategy group
- free-time or special billing rules
- payment merchant mapping and merchant availability
- report/statistics grouping fields

Pitfall: the same lot id or lot number can exist in CPW and main DBs. Always state which DB and schema a row belongs to.

## Phase 3: Device And Lane Binding

Verify:

- `device_list`: device number, type, status, vendor/company, data owner
- `port` or lane table: entry/exit direction, parking lot id, status
- `device_rela`: device id to port/lane id
- middleware-side parking lot/device mapping, if the vendor adapter stores a separate lot no or interface park id
- route path:
  - entry precheck should reach CPW or main route according to deployment
  - exit precheck should reach `/barrier/beforeAway` or `/barrier/beforeAway/self`
  - final exit close should be identified separately from price precheck

Pitfall: a camera can be online while bound to the wrong port or wrong parking lot; verify by `barrier_log.device_id`, `port_id`, and `parking_lot_id`, not by device number alone.

## Phase 4: Parking Business Rules

Verify:

- billing strategy returns expected price for a controlled entry/exit window
- whitelist, blacklist, monthly card, temporary free rules
- auto-pay/ETC readiness only when actual sign assets exist
- manual open or paid-release behavior
- screen/voice/LED behavior if the lot depends on middleware display

Do not claim auto-pay is fully verified without a real signed payment path.

## Phase 5: Charging Add-On

If the lot supports charging, read `charging-addon.md`.

At minimum verify:

- charging station/pile/port belongs to the intended `parking_lot_id`
- charging order can bind `rela_order_id` or `rela_order_no`
- plate number is captured and stored with color where required
- `charging_bonus` contains the lot id if parking-fee waiver is required
- exit `/barrier/beforeAway` with `allowance=0` still gets waiver when a completed charging order exists

## Phase 6: End-To-End Verification

Run a controlled test and record:

- entry event response and `barrier_log`
- main order row and CPW order row if jump mode
- exit precheck response before payment/waiver
- payment row if payment is required
- final away state
- device open-gate evidence if available
- charging order and refund state if charging is involved

Minimum success evidence:

- entry creates one correct active order
- exit uses the intended lot and order
- price matches billing or waiver expectations
- final order is `away/completed` or an explicitly expected state
- no fresh common-error after the test timestamp
