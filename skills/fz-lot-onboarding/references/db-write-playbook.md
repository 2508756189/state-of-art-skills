# Database Write Playbook

Use this when Fengze lot setup requires direct DB changes because an admin/API surface is missing or incomplete.

## Safety Boundary

- Start read-only.
- Discover actual table names and schemas from models or information schema; do not assume `public`.
- Prefer exact primary keys and unique business keys.
- Do not update by name alone when duplicate names can exist across owners or DBs.
- Never bulk update production rows without showing the exact candidate set first.

## Required Write Package

Before writing, prepare:

- target database, schema, and table
- exact rows selected before change
- intended new values
- SQL in a transaction
- rollback SQL
- post-write verification SQL
- whether service restart or cache invalidation is required

## Transaction Pattern

Use this shape for manual SQL:

```sql
begin;

-- 1. lock and show target rows
select ... from ipms.<table>
where <exact filter>
for update;

-- 2. update/insert
update ipms.<table>
set ...
where <same exact filter>
returning ...;

-- 3. verify dependent rows
select ...;

commit;
```

Keep rollback SQL separate and executable. If inserting rows, rollback normally deletes by the generated ids. If updating config JSON, rollback restores the exact prior JSON value.

## JSON Config Updates

For `base_config` JSON such as `charging_bonus`:

- read the full current `value`
- update only the intended nested key
- preserve existing lot entries
- verify the final path, for example `value #> '{value,<parking_lot_id>}'`
- record the previous JSON for rollback

Do not overwrite the entire config object with a single-lot value.

## Cache And Restart

Some changes may be cached. After DB writes, determine whether to:

- refresh Redis permission/config cache
- force user re-login
- restart `parking_platform_service`
- restart `cpw_service`
- restart `barrier_gate_system`

Only restart affected services. Use `production-ops` for backup/restart evidence.

## Verification Queries

After changes, verify from the business path, not only the edited table:

- lot: selected by id and lot no
- devices: device -> relation -> port -> lot
- order path: entry/exit `barrier_log`
- payment: `trade_list_out`, `trade_list_internal`, `refund_list`
- charging: `charging_station`, `charging_pile`, `charging_port`, `charging_order`
