# Code And File Tooling Reference

## Search

Prefer ripgrep:

```powershell
rg --files
rg -n "router.post\\('/bkv" parking_platform_service
rg -n "class Bkv|async startCharge|charge_mode" parking_platform_service/app
```

Use `Get-ChildItem` when directory metadata matters:

```powershell
Get-ChildItem -Path . -Recurse -Filter "*.js" | Select-Object FullName
```

## Read

Use targeted reads:

```powershell
Get-Content -Path "parking_platform_service/app/router.js"
Select-String -Path "parking_platform_service/app/router.js" -Pattern "/bkv/startCharge"
```

For many independent reads, run commands in parallel through the available parallel tool wrapper.

## Edit

Manual edits should use `apply_patch`:

```patch
*** Begin Patch
*** Update File: C:\absolute\path\file.js
@@
-old line
+new line
*** End Patch
```

Do not use these for normal manual edits:

- `cat > file`
- `Set-Content`
- `Add-Content`
- `Out-File`
- Python scripts that rewrite a simple file
- Shell redirection such as `>` or `>>`

Formatting commands or framework generators are acceptable when they are the normal project tool, but inspect results afterward.

## Validate

Pick the smallest useful verification:

- Run targeted unit/integration tests if the project has them.
- Run `rg` to confirm route names, exported functions, or field names exist.
- Run a syntax/lint command when available.
- For DB-related changes, verify with `select` queries.
- For deployment mismatch, compare the deployed route behavior, request logs, and local files.

## Windows Path Notes

- Use quoted paths for Chinese names or spaces.
- Prefer absolute paths in final clickable file links.
- Avoid mixing PowerShell path discovery with destructive `cmd /c` commands.
- Before recursive delete or move, verify the resolved absolute target path is inside the intended workspace.
