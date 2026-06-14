# Fengze CPW Jump Mode

Use this when Fengze is running the Ganzi-style jump pattern: CPW is the gate/cloud-watch jump platform, and normal operator work is done in the main `parking_platform`.

## Production Shape

- Public CPW entry: `https://fengzecj.genchuan.cn:60000/cpw/resource/unattended_admin/index.html#/login`.
- CPW service talks to `cpw_platform`; main platform talks to `fz_parking_platform`.
- CPW `prod-fz` app URLs:
  - `mainPlatformServer`: `MAIN_PLATFORM_SERVER` or `http://127.0.0.1:60061`
  - `barrier`: `http://127.0.0.1:60072`
  - `thirdParty`: `http://127.0.0.1:60071`
  - `parkopen`: public Fengze `/parkopen/service`
- CPW `config.prod-fz.js`:
  - `env.key` is `fzcpw`
  - Sequelize and pg-promise `main/read_only` use `cpw_platform`
  - pg-promise `parking` uses `fz_parking_platform`
  - Redis uses the Fengze host with CPW DB ranges `60-65`
- Main platform `config.prod-fz.js`:
  - Uses `fz_parking_platform`
  - Log DB is `fz_parking_platform_log`
  - Redis uses the Fengze host with main-platform DB ranges `0-5`
- Do not infer production from local `prod-gz` files. Fengze production needs `prod-fz` under `config/build/eggConfig`.

## Jump-Mode Data Rules

- In this mode, users normally operate in the main platform. CPW users are mostly for jump/cloud-watch administration.
- Cloud-watch/CPW-side lots can be default no-charge, matching Ganzi jump mode. Do not blindly copy main-platform billing groups into CPW just because the main platform lot has a billing strategy.
- If CPW logs show `获取计费策略组失败`, first determine whether the current code path is still trying to calculate CPW-side fees. For jump mode, the expected fix may be route/config alignment or a free/no-charge CPW lot setup, not copying the main platform billing strategy wholesale.
- The same lot ID may exist in both databases. Compare `parking_lot.id`, `parking_lot_no`, `logic_type`, `strategy_id`, `data_owner_id`, and device bindings on both sides before changing anything.

## Permission Checks

- CPW permission check path is:
  `base_resource.name -> base_func_permission_resource -> base_role_func_permission -> session.permission.roles`.
- `guest_access=true` bypasses role checks. Otherwise, the role must be linked through `base_func_permission_resource`.
- User permissions are cached in Redis keys:
  - `basePermission:<user_id>`
  - `baseUser:<user_id>`
- Login rebuilds session roles/data owners/depts and writes those Redis keys.
- For Fengze CPW, `qzxlh123` has been observed as a normal CPW admin account under owner `泉州丰泽`, role `系统管理`. Treat it as the known-good CPW-side account when comparing a broken account.
- When a page says `无权限访问当前接口`, check:
  - account status is `in`
  - user has the intended role
  - role has function permissions
  - the failing route exists in `base_resource`
  - route is either `guest_access=true` or linked through `base_func_permission_resource` to a function permission granted to the user's role
  - Redis permission cache was refreshed after permission data changed

## Runtime And Sync Verification

- Expected live ports:
  - `60000`: public nginx/front door
  - `60061`: main platform service
  - `60072`: barrier gateway
  - `60071`: thirdParty, if the deployment uses it
- Order jump flow:
  - CPW entry `/barrier/beforeParking/self` creates/handles CPW-side order then calls main platform `/barrier/parking` with CPW `order_no` as `out_order_no`.
  - CPW exit precheck `/barrier/beforeAway/self` calls main platform `/barrier/beforeAway` with CPW `order_no` as `out_order_no`.
  - CPW final `/barrier/away/self` primarily closes the CPW-side order. Do not assume it calls main `/barrier/away`; verify the current code.
  - Some older/reference main-platform builds include a `cpwSync` controller with `lotSync`, `cardSync`, and `specialSync` for pushing config/business data to CPW. Current Fengze production source may not include that controller; verify `app/router.js` and `app/controller` in the deployed source before assuming it exists.
- To confirm current sync, compare recent orders:
  - CPW: `cpw_platform.ipms.order_list.order_no`
  - Main: `fz_parking_platform.ipms.order_list.out_order_no`
  - Healthy jump sync should show recent CPW orders matched by main `out_order_no`, with acceptable `parking_status/pay_status` differences explained by in-flight entry/exit timing.
- Also compare `barrier_log` across both DBs by `message_id`, `plate_no`, `device_id`, `status`, `process_status`, `error_code`, and timestamp. A high count of `PARKING_PROCESSING` usually means duplicate/in-flight plate handling, while `SYSTEM_ERROR` needs the exact error message.

## Local Sync From Server

- For local source refresh, pull only code/config from the production host into `D:\电动车充电对接文档\甘孜cpw跳板接主平台项目`.
- Do not pull:
  - `node_modules`
  - `logs`
  - `run`
  - `tmp`
  - `*.log`, `*.pid`, especially large files such as `skywalking.log`
- For CPW and main platform, the useful sync set is usually:
  - `app/`
  - `config/`
  - root files such as `app.js`, `agent.js`, `server.js`, `package.json`, `package-lock.json`, `pm2-confg.json`, `README.md`, `CHANGELOG`, `Dockerfile`, `appveyor.yml`
- Pull to a local staging directory first, verify there are no `node_modules` or logs, then copy into the project.
