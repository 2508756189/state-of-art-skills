# SQL Permission and Logical DB Configuration

Use this guide when CPW shows missing menus, missing operator function-permission controls, "无权限", or "逻辑库执行错误".

## Safety rules

- Use the `postgresql-debug` skill for connection and read-only inspection.
- Do not write SQL until the user has asked for a fix and the missing rows are identified.
- Never copy from a reference environment without checking version, product line, tenant/operator scope, and unique keys.
- Before any `INSERT` or `UPDATE`, export/read the target rows and prepare rollback SQL.
- Prefer `INSERT ... SELECT ... WHERE NOT EXISTS` or explicit unique-key checks to avoid duplicates.

## Diagnostic order

1. Confirm which service/database the request reaches:
   - Main platform usually maps to `parking_platform_service`.
   - CPW usually maps to `cpw_service`.
   - CPW data service may be separate from CPW business service.
2. Reproduce or inspect the failing API:
   - 404 suggests missing route or wrong nginx prefix.
   - 200 with `needLogin` or permission error means the route exists and auth is active.
   - "逻辑库执行错误" suggests DB/config/logical schema mismatch.
3. Identify the current tenant/operator/user:
   - Admin user.
   - Role records.
   - Data owner/operator records.
   - Function permission tree records.
4. Compare target rows against a known-good environment with matching CPW version.
5. Insert only missing rows needed for the failing feature.

## Permission tree checks

For operator function permission configuration, verify both frontend and backend support:

- Frontend has permission tree UI strings.
- Backend has:
  - `/develop/dataOwner/showPermission`
  - `/develop/dataOwner/setPermission`
- Controller has `showPermission()` and `setPermission()`.
- Permission/menu tables contain the function tree nodes the UI expects.
- The current admin or operator role can access the developer/data owner permission routes.

## SQL write pattern

Use this sequence:

```sql
begin;

-- 1. Show current target state.
select ... from ... where ...;

-- 2. Show rows to copy from reference/exported values.
-- Keep ids, parent ids, tenant ids, and route/module codes explicit.

-- 3. Insert only missing rows.
insert into target_table (...)
select ...
where not exists (
  select 1 from target_table t where t.unique_col = ...
);

-- 4. Verify exact row count and relationships.
select ... from ... where ...;

-- commit only after verification.
commit;
```

If the application caches permission trees, restart or invalidate only the affected service/cache after SQL writes.

## Red flags

- Main platform menus appearing in CPW usually means the wrong permission tree or logical DB config was copied.
- A system/admin account missing CPW menus often points to missing CPW-side role/function/data-owner records, not only user-account sync.
- New frontend resource can reveal backend route gaps that older frontend never called. Compare route files before blaming data.
