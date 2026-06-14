---
name: fz-lot-onboarding
description: Use when creating, configuring, copying, or validating Fengze parking lots, CPW jump-mode lots, barrier bindings, billing/payment settings, charging-station parking waivers, or database-backed lot setup that lacks admin APIs.
---

# FZ Lot Onboarding

Use this skill for standardizing Fengze "new parking lot / new device / charging-enabled lot" setup. The goal is not just troubleshooting: produce a repeatable configuration package, apply only approved changes, and verify the full entry/exit/payment/charging path.

Pair it with:

- `postgresql-debug` for schema discovery, read-only diffs, and safe writes.
- `production-ops` for server access, backups, upload, service restart, and logs.
- `cpw-production-ops` for CPW jump-mode rules and permission/resource behavior.
- `fz-flow` for entry/exit evidence.
- `fz-hlht-charging-ops` when four-wheel charging, TLD/HLHT, local charging payment, or charging parking-fee waiver is involved.

## Core Rules

- Treat lot setup as a configuration release, not an ad hoc DB edit.
- Produce a configuration package before writing: required inputs, discovered current state, target state, SQL/API actions, rollback SQL, and verification plan.
- Prefer admin/API/config-copy paths when they exist. Use direct DB writes only for missing admin surfaces or proven product gaps.
- Never copy a reference lot blindly. Diff `data_owner_id`, `parking_lot_no`, `logic_type`, billing strategy, payment merchant, device bindings, CPW/main mappings, and charging bindings.
- In Fengze jump mode, CPW is the barrier/cloud-duty jump surface; main platform owns normal parking business and charging business. The same lot can exist in CPW and main DBs with different operational roles.
- Every DB write must be narrow, transactional, reversible, and followed by read verification.
- Do not expose or store passwords, vendor secrets, private keys, payment links, or merchant keys in the skill.

## When Starting

Ask for or discover these inputs:

- lot name, lot code/number, business owner/data owner, region/project
- whether the lot is CPW jump-mode, main-platform-only, or middleware-only
- entry/exit device vendor, device numbers, port/lane names, direction, and physical lane mapping
- billing strategy, free-time rules, whitelist/monthly-card requirements, auto-pay/ETC/payment methods
- whether the lot supports four-wheel charging, charging station/pile/port ids, and charging parking-fee waiver policy
- whether there is a reference lot to copy from
- whether the user wants dry-run only or approved apply

## Workflow

1. Build the target topology:
   - services: `barrier_gate_system`, `cpw_service`, `parking_platform_service`
   - DBs: `cpw_platform`, `fz_parking_platform`, log DBs if needed
   - public routes and local ports
2. Read current state before changing anything:
   - lot rows, ports, devices, device relations, billing strategy, payment merchant, configs, permissions
   - CPW/main mapping through `main.order_list.out_order_no = cpw.order_list.order_no` for jump-mode validation
3. Compare against a reference lot only after confirming the reference is the same business pattern.
4. Generate a configuration package. See [references/automation-contract.md](references/automation-contract.md).
5. Apply changes only after the package is reviewed or the user explicitly asks for direct execution.
6. Verify with the standard checklist. See [references/standard-flow.md](references/standard-flow.md).

## What To Read

- For the full create/configure/verify checklist, read [references/standard-flow.md](references/standard-flow.md).
- For direct database writes and rollback requirements, read [references/db-write-playbook.md](references/db-write-playbook.md).
- For AI-generated configuration packages, read [references/automation-contract.md](references/automation-contract.md).
- For four-wheel charging and parking-fee waiver add-ons, read [references/charging-addon.md](references/charging-addon.md).

## Output Shape

For setup tasks, respond with:

- `current_state`: what exists and what is missing
- `target_config`: target topology and business rules
- `execution_method`: API/admin action vs DB write vs file config/restart
- `risks`: ambiguous or dangerous fields
- `change_list`: exact rows/files/config keys to change
- `rollback`: rollback SQL or backup paths
- `verification`: entry, exit, payment, charging waiver, logs

If the user asks for automation, provide the package first; execute only when the user has provided enough identifiers and has asked to apply.
