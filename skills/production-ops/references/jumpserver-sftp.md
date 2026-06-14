# JumpServer and SFTP

Use this guide when moving resources, reading remote files, or entering a production host through JumpServer.

JumpServer is for host access, not a default path for database queries. If the
user already gave a reachable PostgreSQL endpoint, use direct DB access first
and only use JumpServer for server-only checks or in-process execution on the
host.

## WinSCP batch pattern

Use the local WinSCP CLI when available:

```powershell
& 'C:\Program Files (x86)\WinSCP\WinSCP.com' /ini=nul /command `
  'option batch abort' `
  'option confirm off' `
  'open sftp://<user>@<jump-host>:12222/ -privatekey="<key-path>" -hostkey="*"' `
  'ls /Default/Linux/生产环境' `
  'exit'
```

Prefer the bundled helper:

```powershell
powershell -ExecutionPolicy Bypass -File <skill>/scripts/invoke-winscp-jumpserver.ps1 `
  -User <jump-user> `
  -KeyPath 'D:\下载\wsh_new.jumpserver.ppk' `
  -Command 'ls /Default/Linux/生产环境'
```

Notes:

- Use single quotes around WinSCP command strings in PowerShell when paths contain Chinese characters.
- `-hostkey="*"` is convenient for JumpServer sessions but less strict. If a stable host key is known, use it.
- `cp` may be unsupported by the SFTP backend. Use `get` to local plus `put`, or `mv` for same-filesystem backups.
- Use `option batch continue` only for optional probes where missing files are acceptable.

## Safe remote file replacement

For directories:

1. Upload or synchronize to a remote staging directory.
2. Verify expected files in staging.
3. Rename current directory to `*_bak_YYYYMMDD_HHMM`.
4. Rename staging directory to the production name.
5. Keep the backup until the UI and service are verified.

For single files:

1. Download current file to local `tmp/remote_backups`.
2. Rename remote file to `file.ext.bak.YYYYMMDD_HHMM`.
3. Upload patched file to the original path.
4. Download the final remote file and grep for the expected change.

## Interactive shell through JumpServer

For command execution through JumpServer, use this order. Do not re-probe every possible tool on each task.

0. Confirm network reachability first. Home, office, VPN, and allow-list positions can differ; if both bastion and direct host ports time out, suspect network path before credentials.
1. Primary path: Python `paramiko` helper with the PEM key.
2. If `paramiko` is missing, install it once with `python -m pip install paramiko`.
3. If install fails or Python cannot connect, then fall back to WinSCP/SFTP or a manual interactive shell.
4. Use WinSCP primarily for file transfer; do not use WinSCP `call` as the first choice for remote commands.

Use a PEM key and the Python helper:

```powershell
python <skill>/scripts/jumpserver-shell-run.py `
  --jump-host <jump-host> --port 12222 `
  --user <jump-user> --key 'D:\下载\wsh_new.jumpserver.pem' `
  --target 10.0.0.3 `
  --command 'pwd' `
  --command 'ps -ef | grep cpw_platform | grep -v grep'
```

For commands with nested quotes or longer multi-step checks, prefer a UTF-8
command file over inline quoting:

```powershell
python <skill>/scripts/jumpserver-shell-run.py `
  --jump-host <jump-host> --port 12222 `
  --user <jump-user> --key 'D:\downloads\wsh_new.jumpserver.pem' `
  --target 10.0.0.3 `
  --command-file .\jumpserver-commands.txt
```

On Windows, create command files without BOM when possible:

```powershell
[System.IO.File]::WriteAllLines((Resolve-Path .).Path + '\jumpserver-commands.txt', $commands, [System.Text.UTF8Encoding]::new($false))
```

The JumpServer menu search can return multiple assets. Always confirm the selected host name and IP before running write or restart commands.

If the bastion key is unavailable and the user explicitly authorizes direct host credentials, direct SSH/SFTP can be used as a fallback. Keep the same safety sequence: inspect first, back up files, upload only intended paths, preserve owner/mode, and restart as the service runtime user rather than as root.

If the launcher machine is Windows and the menu or command output contains
Chinese text, set the console to UTF-8 before invoking helpers to reduce
garbling:

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
chcp 65001 > $null
```
