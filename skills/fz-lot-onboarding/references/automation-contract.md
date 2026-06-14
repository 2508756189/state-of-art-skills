# Automation Contract

Use this when the user wants AI to configure a Fengze lot automatically or semi-automatically.

## Required Inputs

The AI should collect or discover:

- target environment and DBs
- data owner/operator
- lot name and lot no
- reference lot id/no, if copying
- device list with physical lane direction
- billing strategy and payment method
- jump-mode requirement
- charging requirement and parking-fee waiver policy
- whether direct DB writes are approved

## Dry-Run Output

Before applying, output a configuration package:

```yaml
lot:
  target_db:
  data_owner_id:
  parking_lot_id:
  parking_lot_no:
  logic_type:
reference:
  lot_id:
  lot_no:
changes:
  api_actions: []
  db_inserts: []
  db_updates: []
  file_changes: []
risks: []
rollback:
  sql_files: []
verification:
  sql: []
  live_tests: []
```

The package should include exact SQL filters or state that more identifiers are required. It should not include secrets.

## Apply Rules

- If the user asked only for a plan, do not write.
- If the user asked to apply and identifiers are sufficient, execute in small phases:
  1. base lot/config
  2. device/lane binding
  3. billing/payment
  4. charging add-on
  5. verification
- After each phase, run verification before moving to the next.
- Keep rollback SQL or backups from each phase.

## AI-Friendly Checks

The AI should be able to answer after setup:

- Which DB and schema owns each row?
- Which route handles entry?
- Which route handles exit precheck?
- Which row binds device to lane?
- Which config controls price/free time?
- Which merchant handles payment/refund?
- If charging exists, which station/pile/port maps to the lot?
- If charging waiver exists, what proves `allowance=0` still waives parking?

## Stop Conditions

Stop and ask before writing when:

- duplicate lots or devices match the same business key
- reference lot has a different `logic_type` or business owner
- payment merchant is missing or ambiguous
- physical lane direction is unknown
- charging connector ids do not match vendor ids
- rollback cannot be produced
