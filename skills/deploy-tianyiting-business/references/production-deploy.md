# tianyiting_business Production Deployment Reference

## Recommended .env.production for 方案 A

Use this mode when PostgreSQL already exists outside Docker:

```env
NODE_ENV=production
JWT_SECRET=CHANGE_TO_A_LONG_RANDOM_SECRET
JWT_EXPIRES_IN=7d

BASE_URL=http://SERVER_IP:3001
BACKEND_PORT=3001
FRONTEND_PORT=8081
UNIAPP_PORT=8082

DB_HOST=POSTGRES_HOST
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=POSTGRES_PASSWORD
DB_DATABASE=tianyiting_business

WECHAT_MP_APPID=
WECHAT_MP_APPSECRET=
WECHAT_MP_REDIRECT_URI=
WECHAT_MP_SCOPE=snsapi_base
WECHAT_MP_NOTIFY_URL=
WECHAT_MP_TEMPLATE_MAP={}

VITE_H5_MAP_DEFAULT_PROVIDER=osm
VITE_H5_MAP_TIANDITU_KEY=7e52669d1dc562120fb764741f703b0f
VITE_H5_MAP_TENCENT_KEY=
VITE_H5_MAP_AMAP_KEY=
```

If WeChat official-account push is later enabled, fill `WECHAT_MP_APPID`, `WECHAT_MP_APPSECRET`, `WECHAT_MP_NOTIFY_URL`, and a real `WECHAT_MP_TEMPLATE_MAP`.

## Database Backup

Run before any production SQL upgrade:

```bash
pg_dump -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -Fc -f backup_tianyiting_$(date +%Y%m%d_%H%M%S).dump
```

If `psql` or `pg_dump` is not installed on the app server, run from a DB tool, the DB server, the user's local machine, or a temporary Docker PostgreSQL client.

## Incremental SQL Order

For an existing production DB:

```bash
psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f init/04-update-operation-log-types.sql
psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f init/05-region-and-flow-update.sql
psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f init/06-auth-login-security.sql
psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f init/07-login-failure-notification.sql
```

Then execute the production-safe `08` structure SQL below. Do not run the seed/test-data inserts from the full `init/08-region-manager-location-amount-notify.sql` unless explicitly requested.

```sql
ALTER TABLE "region"
  ADD COLUMN IF NOT EXISTS "manager_user_id" VARCHAR(50),
  ADD COLUMN IF NOT EXISTS "manager_user_name" VARCHAR(50);

ALTER TABLE "region"
  DROP CONSTRAINT IF EXISTS "fk_region_manager_user";

ALTER TABLE "region"
  ADD CONSTRAINT "fk_region_manager_user"
  FOREIGN KEY ("manager_user_id") REFERENCES "user" ("id") ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS "idx_region_manager_user_id" ON "region" ("manager_user_id");

ALTER TABLE "business_opportunity"
  ADD COLUMN IF NOT EXISTS "estimated_amount" DECIMAL(12, 2),
  ADD COLUMN IF NOT EXISTS "location_name" VARCHAR(120);

CREATE INDEX IF NOT EXISTS "idx_opportunity_estimated_amount"
  ON "business_opportunity" ("estimated_amount");

CREATE INDEX IF NOT EXISTS "idx_opportunity_assigned_region_status"
  ON "business_opportunity" ("assigned_region_id", "status");

ALTER TABLE "notification"
  DROP CONSTRAINT IF EXISTS "notification_type_check";

ALTER TABLE "notification"
  ADD CONSTRAINT "notification_type_check"
  CHECK (
    type IN (
      'new_opportunity',
      'review_result',
      'dispatch',
      'accept',
      'reject',
      'timeout',
      'report',
      'login_failure',
      'close',
      'revoke_dispatch'
    )
  );
```

## Run SQL Without psql on App Server

Use a DB GUI and paste the scripts, or use Docker as a client:

```bash
docker run --rm \
  -e PGPASSWORD='<DB_PASSWORD>' \
  -v "$PWD/init:/sql:ro" \
  postgres:15-alpine \
  psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f /sql/04-update-operation-log-types.sql
```

For ad hoc SQL saved as `/tmp/tianyiting-08-prod.sql`:

```bash
docker run --rm \
  -e PGPASSWORD='<DB_PASSWORD>' \
  -v /tmp:/tmp:ro \
  postgres:15-alpine \
  psql -h <DB_HOST> -p 5432 -U <DB_USERNAME> -d tianyiting_business -f /tmp/tianyiting-08-prod.sql
```

## Clear Old Containers Safely

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
docker rm -f tianyiting-backend tianyiting-frontend tianyiting-mobile
```

Do not delete `backend_uploads` unless the user explicitly confirms uploaded files can be removed.

Optional image cleanup:

```bash
docker image prune -f
```

## Deploy

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
```

## Smoke Tests

```bash
curl http://SERVER_IP:3001/api/v1/dashboard/statistics
```

`401` means the backend is reachable and auth is required. `500` usually points to incomplete DB upgrade or runtime config problems.

Visit:

- backend API: `http://SERVER_IP:3001/api/v1`
- admin frontend: `http://SERVER_IP:8081`
- H5: `http://SERVER_IP:8082`
