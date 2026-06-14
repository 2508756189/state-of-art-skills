---
name: cpw-production-ops
description: "Use for Tianyi Parking CPW and parking_platform product-specific production issues: cpw_resource frontend sync, cpw_service or parking_platform_service route/config behavior, CPW jump-mode logic, PostgreSQL menu/permission/logical database data, operator/admin permission trees, Fengze/Ganzi deployment conventions, and charging jump-mode configuration. For generic JumpServer/SFTP/server restart mechanics, pair with production-ops."
---

# CPW Production Ops

Use this skill for Tianyi Parking CPW and parking-platform product knowledge. It explains how CPW, main platform, resources, permission data, and Fengze/Ganzi jump-mode conventions fit together.

Use `production-ops` for generic server mechanics such as JumpServer access, SFTP upload, timestamped file backups, Linux process discovery, and service restarts. Use `postgresql-debug` for generic PostgreSQL inspection and write safety. This skill adds the Tianyi-specific interpretation on top.

For new Fengze parking-lot onboarding, barrier/device binding, billing/payment setup, or charging-enabled lot configuration, use `fz-lot-onboarding` first; use this skill as the CPW/main-platform product reference during that flow.

## Safety posture

- Treat production as live: read first, write only when the user clearly asks for a fix.
- Do not store or repeat database passwords, private key contents, session cookies, or vendor charging secrets in skill files or final summaries.
- Never modify Ganzi or another reference environment while using it for comparison.
- Prefer copying known-good records/resources from the closest matching environment over inventing values.
- For file changes, follow `production-ops` backup and upload rules.
- For SQL writes, run a read-only diff first, wrap writes in a transaction, and record rollback SQL.

## Fast workflow

1. Identify the failing surface: main platform, CPW developer, CPW unattended admin, shared `cpw_service`, charging middleware, or frontend resource.
2. Confirm whether it is frontend, backend route, logic DB config, permission/menu data, or vendor/device data:
   - Frontend missing UI: inspect `cpw_resource/<module>/index.html` build hash and bundle strings.
   - Backend missing capability: compare `app/router.js` and controller methods.
   - Logical database error: inspect logic DB mapping and actual service logs before changing data.
   - No permission or missing menu: inspect user role, operator/data owner, function tree, and permission mapping.
   - Charging callback blocked: check `base_resource.guest_access` for device/vendor callback routes before changing service code.
3. Compare against a reference environment with the same CPW version. Use SaaS or Pingtan for newer CPW capabilities; use Ganzi only as a reference and do not change it.
4. Apply the smallest complete fix:
   - Resource issue: replace only the target `cpw_resource` module.
   - Missing backend route: add only the route lines if the controller already exists.
   - Missing data: insert/update only the missing permission/menu/config records.
   - Charging jump mode: keep CPW as the barrier/cloud-duty jump surface; put charging business data in the main platform.
5. Restart only the affected service and verify endpoints/resources externally.

## Tianyi/Fengze Environment Patterns

- Generic JumpServer/SFTP usage lives in `production-ops`; load that skill for helper commands.
- Fengze main platform business DB is `fz_parking_platform`, schema `ipms`.
- CPW logical DBs are not the place for charging station, pile, port, or charging-order business data in jump mode.
- Important CPW paths often follow:
  - Fengze frontend: `/Default/Linux/生产环境/泉州丰泽停车服务器/Qzfz_web_node_10.0.0.3/file_server/cpw_resource`
  - Fengze CPW service: `/Default/Linux/生产环境/泉州丰泽停车服务器/Qzfz_web_node_10.0.0.3/data/projects/cpw_service`
  - Fengze main platform service: `/Default/Linux/生产环境/泉州丰泽停车服务器/Qzfz_web_node_10.0.0.3/data/projects/parking_platform_service`
  - Fengze barrier middleware: `/Default/Linux/生产环境/泉州丰泽停车服务器/Qzfz_web_node_10.0.0.3/data/projects/barrier_gate_system`
  - SaaS CPW resource reference: `/Default/Linux/生产环境/saas原子能力平台/saas_web-ndoe-01_10.0.120.16/file_server/cpw_resource`

## What to read next

- For JumpServer and SFTP operations, use the `production-ops` skill.
- For frontend resource comparison and deploy, read [references/cpw-resource-sync.md](references/cpw-resource-sync.md).
- For Fengze/Ganzi CPW jump-mode production checks, read [references/fengze-jump-mode.md](references/fengze-jump-mode.md).
- For Fengze charging jump-mode configuration, read [references/fengze-charging-jump-mode.md](references/fengze-charging-jump-mode.md).
- For permission/menu/logical DB SQL work, read [references/sql-permission-config.md](references/sql-permission-config.md).
- For service discovery, restart, and verification, use `production-ops`.
- If PostgreSQL inspection is needed, also use the `postgresql-debug` skill for safe query execution.
- If the task is specifically about Fengze entry/exit flow validation, use `fz-flow`.

## Verification checklist

- Public resource URL returns the expected build hash.
- New or changed backend route returns HTTP 200 and a permission/login/business-validation response, not 404.
- Service process has a new start time after restart and listens on the expected port.
- UI is checked with a logged-in account after clearing cache or hard-refreshing.
- Permission SQL is verified from `base_resource`, role/menu tables, or the relevant product-specific table.
- Charging data is verified from `fz_parking_platform.ipms` and not from a CPW logical database unless the question is explicitly about CPW jump behavior.
- Backups and rollback SQL are named in the final summary with exact paths.
