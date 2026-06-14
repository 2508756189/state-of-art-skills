# CPW Resource Sync

Use this guide when CPW pages are missing modules, menu features, or UI controls because the deployed frontend resource is stale or mismatched.

## Decide whether to copy resources

Copy frontend resources only after confirming:

- The target page loads an older or wrong build hash.
- The reference bundle contains the missing capability strings.
- The backend route/controller capability exists or can be minimally added.
- The source module matches the target product line (`cpw_resource/developer`, `cpw_resource/unattended_admin`, etc.).

Do not blindly replace the whole `cpw_resource` directory. Replace only the module that owns the missing UI.

## Useful checks

List remote module timestamps:

```powershell
<winscp> 'ls /.../file_server/cpw_resource'
```

Download or inspect key files:

- `index.html` for build hash.
- `main.<hash>.js` for app-level config.
- numbered chunk files for feature components.

Search bundles for feature strings:

```powershell
Select-String -Path 'tmp\module\*.js' -Pattern `
  'func_permission_tree','permissionTree','showPermission','setPermission'
```

For the CPW operator permission UI, a compatible developer bundle should contain:

- `func_permission_tree`
- `permissionTree`
- `getSelectedPermissions`
- `transformSelectedData`
- `onPermissionSubmit`
- routes or API configs for `/develop/dataOwner/showPermission` and `/develop/dataOwner/setPermission`

## Known CPW modules

- `developer`: logical DB/developer/admin style configuration UI, including operator/data owner permission configuration in newer builds.
- `unattended_admin`: unattended/lot/device management UI. Do not downgrade it just to fix developer permission configuration.

## Deploy pattern

1. Pull source module locally with WinSCP `synchronize local -mirror`.
2. Search local bundle for the missing capability.
3. Upload to target staging path:
   `cpw_resource/<module>_stage_YYYYMMDD_HHMM`.
4. Rename current target module to:
   `<module>_bak_YYYYMMDD_HHMM`.
5. Rename staging to the production module name.
6. Verify public URL, for example:
   `https://<domain>/cpw/resource/developer/index.html`.

The expected public `index.html` should reference the new build hash. If the browser still shows the old UI, hard-refresh or clear cache before continuing.
