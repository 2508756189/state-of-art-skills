# Service Management

Use this guide after changing backend code/routes/config or after SQL writes that require cache/process refresh.

## Discover the service manager

On the target host, inspect before restarting:

```bash
pwd
whoami
command -v pm2 || true
pm2 ls || true
ps -ef | grep -E 'cpw_platform|cpw_service|parking_platform|egg|node' | grep -v grep
ss -lntp | grep <port> || netstat -lntp 2>/dev/null | grep <port> || true
```

Do not assume pm2 owns every Egg service. Some services run via `egg-scripts` directly and therefore may not appear in `pm2 ls`.

Non-interactive SSH sessions, especially as root, may not have the service's Node.js path. If `node` or `npm` is missing, inspect the running process or service user's environment and use the deployed runtime path explicitly.

When files are uploaded by root or another maintenance account, restore the original owner and mode from the backup before restart. Restart as the existing runtime user with the same environment variables and PATH shape that the service already uses.

## CPW service pattern

For Fengze CPW:

- Project: `/data/projects/cpw_service`
- Package title: `cpw_platform`
- Port: `60261`
- Stop: `npm run stop`
- Start: `npm run start`

Expected start output:

```text
egg started on http://127.0.0.1:60261
```

The process command should include:

```text
baseDir":"/data/projects/cpw_service"
title":"cpw_platform"
port":60261
```

## Restart safely

1. Confirm the exact project directory and title from `package.json`.
2. Confirm the current listening port.
3. Stop/start only the affected project:

```bash
cd /data/projects/cpw_service
npm run stop
npm run start
```

4. Verify process and port:

```bash
ps -ef | grep -E 'cpw_platform|/data/projects/cpw_service' | grep -v grep
ss -lntp | grep 60261
```

After restart, filter logs by the restart timestamp. Old historical errors in long-lived log files should not be reported as new release failures.

## Endpoint verification

For a newly added route, test locally first:

```bash
curl -s -o /tmp/cpw_route.out -w '%{http_code}' \
  -X POST http://127.0.0.1:60261/develop/dataOwner/showPermission
echo
head -c 300 /tmp/cpw_route.out
```

A permission/login response with HTTP 200 proves the route is mounted. A 404 means route or nginx path is wrong. A crash or 500 means inspect service logs before continuing.

Then verify through the public nginx prefix, for example:

```powershell
Invoke-WebRequest -UseBasicParsing -Method Post `
  -Uri 'https://<domain>/parking/service/develop/dataOwner/showPermission'
```

For frontend verification, fetch the public `index.html` and confirm the new hash appears.
