---
name: production-ops
description: "Use for general production operations that are not tied to one product: JumpServer or bastion access, SFTP file upload/download, timestamped remote backups, Linux service discovery, Node/Egg/pm2 restarts, port/process checks, endpoint smoke tests, and safe handling of production files or configuration."
---

# Production Ops

Use this skill for cross-project production mechanics. Keep product-specific business rules in that product's skill, and use this skill for reaching servers, replacing files safely, restarting services, and verifying the result.

## Safety posture

- Treat production as live: inspect first, write only when the user clearly asks for a change.
- Do not store or repeat passwords, private keys, cookies, or production tokens in skill files or final summaries.
- Before replacing a remote file, download or rename a timestamped backup.
- Before SQL writes, use the relevant database skill and run a read-only diff first.
- Restart only the affected service and confirm process, port, and endpoint behavior afterward.
- Keep final summaries specific: what changed, where backups live, what was verified, and what risk remains.

## Access path boundary

Do not blur database access and server access:

- Use JumpServer or SSH for host-only work:
  - reading app config on the server
  - checking processes, ports, logs, and deployed paths
  - running in-process scripts on the app host
  - uploading files or restarting services
- Do not use JumpServer merely because it exists. If the user already gave a
  directly reachable DB endpoint, query the database directly and stay out of
  the bastion path.
- Do not assume VPN or bastion is always required. Home, office, and server
  allow-list positions may differ; test the specific host/port before treating
  a timeout as a credential or service failure.
- If both paths are needed in one incident, state the split explicitly:
  - database inspection is direct to PostgreSQL
  - service inspection is through JumpServer to the host

## Shortest path checklist

Use this exact decision order:

1. The user asks to query data and already supplied DB credentials:
   do not SSH first; use `postgresql-debug`.
2. The user asks about processes, ports, deployed files, logs, or service-side
   execution:
   use JumpServer or SSH.
3. The user asks for both:
   say which facts come from direct DB access and which come from host access.

Avoid these detours:

- do not treat the bastion as a required first hop for every production task;
- do not use server login to rediscover values the user already provided;
- do not conflate "the database lives on that host" with "the query must be
  executed through that host".

## Fast workflow

1. Confirm the target host, path, service name, and port from current config or process output.
2. Read current state before changing it:
   - `pwd`, `whoami`, `ps -ef`, `ss -lntp`, `pm2 ls`, `package.json`, and the target config file.
3. For file changes:
   - run local syntax/tests first when possible;
   - back up the remote file or directory;
   - upload only the intended file set;
   - preserve original owner and mode when upload user differs from runtime user;
   - run remote syntax checks before restart.
4. Restart using the service's existing mechanism, runtime user, and environment, such as `npm run stop && npm run start`, `pm2 restart`, or the local supervisor command.
5. Verify:
   - process is running;
   - expected port is listening;
   - local endpoint returns the expected status;
   - public URL works if a public proxy is part of the path.

## AI-assisted publish workflow

When the user asks Codex to publish, update production, restart, or sync current code to a server, follow the dedicated checklist in [references/ai-publish-workflow.md](references/ai-publish-workflow.md). This workflow is mandatory for production-like releases because it captures the safe sequence: local diff, targeted file list, remote backup, upload, remote syntax check, restart, route/port/log verification, and rollback notes.

## Shell encoding hygiene

On Windows launchers, force UTF-8 before reading Chinese output or relaying it
back to the user. This matters for JumpServer menus, `Get-Content`, and
PowerShell command output.

Use:

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
chcp 65001 > $null
```

If a file is still garbled after that, treat it as a file-encoding issue and
retry with an explicit `-Encoding` instead of assuming the remote content is
bad.

## What to read next

- For JumpServer, WinSCP, SFTP, and shell helper usage, read [references/jumpserver-sftp.md](references/jumpserver-sftp.md).
- For Node/Egg/pm2 service discovery, restart, and smoke-test patterns, read [references/node-service-management.md](references/node-service-management.md).
- For AI-driven production publishing and restart handoffs, read [references/ai-publish-workflow.md](references/ai-publish-workflow.md).
- For PostgreSQL inspection or SQL writes, use the `postgresql-debug` skill; do not duplicate database credentials or query helpers here.

## Verification checklist

- Backup path or remote `.bak_<timestamp>` is recorded.
- Uploaded files match the intended list.
- Remote syntax checks pass for changed code/config.
- Service process has a fresh PID or start time after restart.
- Expected port is listening.
- Smoke-test response proves the route/config is active, not just that the process started.
