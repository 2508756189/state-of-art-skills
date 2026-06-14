# AI Publish Workflow

Use this reference when the user asks Codex to publish local code to a server, restart a service, or continue a previous AI-assisted deployment. Keep the workflow operational and evidence-based: do not claim success until the remote service is verified after restart.

## Placement

This belongs under `production-ops`, not a new standalone skill, because it is a generic production operation pattern. Product-specific skills such as `cpw-production-ops` should add business interpretation on top, but remote backup, upload, restart, and verification mechanics stay here.

## Trigger phrases

Use this checklist for requests such as:

- "发布重启"
- "把代码更新到服务器"
- "同步到生产"
- "继续发布"
- "通过堡垒机连一下服务器"
- "看看服务器有哪些更新"
- "当前代码是否可以发布到生产"

## Required decision boundary

Before changing production, identify whether the task is one of these:

1. **Inspect only**: compare local and remote files, process state, config, logs, or DB facts. Do not write files or restart.
2. **Deploy only**: upload a known local change set and restart only the affected service.
3. **Deploy plus data**: code release plus permission/menu/config SQL. Use `postgresql-debug` for DB inspection and write safety; do not hide DB writes inside a deploy.

If the user only asked for inspection, stop before upload/restart. If the user clearly asked to publish/restart, proceed without asking for another confirmation unless target identity is ambiguous.

## Pre-flight

1. Confirm local repo, branch, and changed files:
   - `git status --short`
   - inspect only the relevant diff or file list
   - avoid deploying unrelated local edits
2. Confirm target host and service facts:
   - jump/bastion address and key or normal SSH path
   - remote app path
   - service start/stop mechanism
   - expected port
   - whether the current network location needs VPN, bastion, or direct host access
   - runtime path if system `node` is not reliable
3. Run local validation for changed code:
   - for Node/Egg services, run `node --check` on changed JavaScript files when tests are not practical
   - run targeted tests only when available and reasonably scoped
4. Announce the intended file list before writing remote files.

## Remote safety sequence

Use this exact order for file deployments:

1. Connect to the target host and verify `whoami`, `hostname`, `pwd`, and app path.
2. Inspect the current service command from `package.json`, `pm2 ls`, supervisor config, or existing scripts.
3. Create timestamped backups of every remote file that will be overwritten:
   - prefer `file.ext.bak_YYYYMMDD_HHMMSS`
   - for new files, record that rollback means removing or leaving the unused file
4. Download remote backups locally when feasible, especially for production services.
5. Upload only the intended file set.
6. Restore owner/mode from the backup when upload user differs from runtime user, then verify remote file size/timestamp or checksum.
7. Run remote syntax checks before restart:
   - use the service's real runtime, for example `/data/nodejs/node-v16.20.2-linux-x64/bin/node --check app/router.js`
8. Restart only the affected service with its existing mechanism, runtime user, and environment, for example `npm run stop && npm run start`.
9. Verify fresh process and port:
   - process has a new PID or start time
   - expected port is listening
10. Smoke test a stable endpoint and at least one changed route:
   - login-required response is valid for authenticated routes
   - 404 means the route probably did not load
   - vendor callbacks may need `guest_access`; admin routes usually should not be anonymous
11. Check startup/error logs after restart.

## JumpServer and Windows hygiene

- Set `$env:PYTHONIOENCODING='utf-8'` before using JumpServer helper scripts from PowerShell.
- If both bastion and direct host probes time out, check VPN/network location before changing credentials or commands.
- Write remote command files as ASCII or UTF-8 without BOM; a BOM can turn the first remote command into an invalid command.
- Keep remote inline commands simple. For complex JSON payloads, prefer a command file or a small remote script.
- Treat JumpServer SFTP single-file `ls` failures cautiously; verify with remote shell `ls -l` if directory listing shows the upload exists.
- Root or non-interactive shells may not have the runtime `node`/`npm` PATH; inspect the running process or use the deployed runtime path explicitly.
- Do not print private keys, DB passwords, cookies, or vendor payment secrets in final summaries.

## Verification evidence to collect

Final summaries should include enough evidence for the user to trust the release:

- remote app path
- files uploaded
- remote backup paths
- local backup path if downloaded
- remote syntax-check result
- restart command used
- old and new PID or new start time
- port-listening evidence
- smoke-test response
- startup/error-log finding
- route exposure conclusion when routes changed

## Route and permission interpretation

When a deployment adds routes, distinguish these cases:

- **Admin or operation routes**: should normally return a login/permission response without a token. Do not add `guest_access=true` just to make smoke tests return business data.
- **Vendor callback routes**: may need anonymous `guest_access=true` or equivalent middleware bypass, because external vendors cannot hold platform login state.
- **Frontend menu/button routes**: may require resource/menu/role permission data after backend publish. This is not the same as anonymous exposure.
- **Proxy/public routes**: verify both local service port and public proxy when the public path matters.

## Rollback notes

Always leave the user with a rollback path:

- list each `.bak_<timestamp>` file
- identify new files that did not exist before deployment
- state the restart command needed after rollback
- do not execute rollback unless the user asks or verification proves the release is broken

## Final answer pattern

Use a short operational summary:

- lead with `已发布并重启成功` or the exact blocker
- list uploaded files and backups
- list verification evidence
- call out any route/permission/data follow-up
- never include secrets

If verification is incomplete, say exactly what is missing instead of implying success.
