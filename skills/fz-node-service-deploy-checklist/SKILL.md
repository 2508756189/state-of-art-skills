---
name: fz-node-service-deploy-checklist
description: Use for Fengze (`fz`) Node service deploys when code, SQL, restart mode, and smoke verification all matter, especially `parking_platform_service` or `barrier_gate_system` releases through JumpServer where the process manager, port, backup, and smoke route must be verified before claiming success.
---

# FZ Node Service Deploy Checklist

Use this for Fengze `parking_platform_service`, `barrier_gate_system`, or closely related Node service rollouts. It is designed to avoid repeated mistakes around assumed process managers, partial SQL/code deploys, missing backups, and weak smoke verification.

Pair with:

- `production-ops` for JumpServer, SFTP, backups, restart mechanics, and log checks.
- `cpw-production-ops` or `fz-hlht-charging-ops` for product-specific business interpretation.
- `postgresql-debug` when SQL or production data verification is involved.

## Scope Guard

- Confirm the exact target environment first. If the user says "only fz" or names a single site, do not touch comparison or reference environments.
- Build a precise deploy set: changed code files, matching SQL scripts, and any config files. Avoid repo-wide uploads.
- Read current production state before writing. Treat live services as production unless proven otherwise.

## Known Fengze Evidence

Recheck these on every run before restart because they can drift:

- `parking_platform_service`: service root `/data/projects/parking_platform_service`; has run as an Egg service on port `60061` with `EGG_SERVER_ENV=prod-fz`.
- `barrier_gate_system`: service root `/data/projects/barrier_gate_system`; has run under PM2 as `barrier_gate_system` on port `60072`.

## Procedure

1. Identify target host, service root, changed file list, and whether SQL is required.
2. Determine the real process model before writing restart commands:
   - inspect `package.json` scripts;
   - inspect `pm2 ls` when PM2 may be involved;
   - inspect `ps -ef` for `egg-scripts`, service title, env vars, and node path.
3. Run local gates:
   - `node --check` for touched JS files;
   - narrow regression tests if they exist;
   - SQL syntax/schema checks when SQL is part of the deploy.
4. Back up each remote file before overwrite with a timestamped backup path.
5. Apply SQL before restart if new code depends on new tables or columns; verify the target objects after execution.
6. Upload only intended files.
7. Run remote syntax checks on changed JS files.
8. Restart using the verified process model and existing env.
9. Verify in order:
   - process is up;
   - expected port is listening;
   - smoke route returns non-404;
   - invalid or empty probe returns the expected business-error shape;
   - log tail has no immediate startup or syntax exceptions.

## Practical Shortcuts

- For JumpServer command quoting, prefer generated command files or a Python helper over complex inline PowerShell strings.
- A minimal empty POST is often enough to prove route registration before sending complex JSON.
- If old logs contain similar errors, use a time window around restart instead of treating all historical errors as new.
- If a restart command says the process does not exist, stop and rediscover the process model; do not keep retrying the same command.

## Verification Checklist

- Target environment and "do not touch" environments are stated.
- Backup paths are recorded.
- SQL was applied only when required and target schema objects were verified.
- Local and remote syntax checks passed.
- Correct runtime manager was identified.
- Restart completed without ambiguity.
- Port and smoke route were verified.
- Fresh logs show no immediate errors.
