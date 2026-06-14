---
name: deploy-tianyiting-business
description: Deploy, upgrade, or troubleshoot the tianyiting_business opportunity-management system on a server. Use when the user asks about production Docker Compose deployment, clearing old containers, using docker-compose.prod.yml, connecting to an existing PostgreSQL database, manually applying init SQL scripts, preserving uploads, configuring .env.production, H5 map keys, or postponing WeChat official-account integration.
---

# Deploy Tianyiting Business

## Core Workflow

Use this skill for the `tianyiting_business` project deployment flow. First inspect the current repo files if available, especially `docker-compose.prod.yml`, `.env.production.example`, `init/`, and `deploy/production/`. Then choose the deployment mode:

- **Plan A: existing PostgreSQL**: use `docker-compose.prod.yml`; start only `backend`, `frontend`, and `uniapp`; manually upgrade the database.
- **Plan B: Docker PostgreSQL**: use `docker-compose.yml`; useful for local or test servers where a fresh DB can be initialized from `init/`.

Prefer Plan A for production unless the user explicitly wants a self-contained test deployment.

## Plan A Checklist

Before starting services:

- Create `.env.production` from `.env.production.example`.
- Fill `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, `JWT_SECRET`, `BASE_URL`, `BACKEND_PORT`, `FRONTEND_PORT`, and `UNIAPP_PORT`.
- Keep WeChat official-account settings empty when official-account integration is postponed:
  - `WECHAT_MP_APPID=`
  - `WECHAT_MP_APPSECRET=`
  - `WECHAT_MP_REDIRECT_URI=`
  - `WECHAT_MP_NOTIFY_URL=`
  - `WECHAT_MP_TEMPLATE_MAP={}`
- Keep the H5 map build variables, especially `VITE_H5_MAP_TIANDITU_KEY`, because they are injected during `uniapp` Docker build.

Use `docker-compose.prod.yml`, not the older compose that lacks `WECHAT_MP_NOTIFY_URL`, `WECHAT_MP_TEMPLATE_MAP`, or `uniapp.build.args` for map keys.

## Database Upgrade

Never assume `psql` is installed on the application server. If `psql` is missing, recommend one of:

- run SQL directly in Navicat, DBeaver, DataGrip, pgAdmin, or another DB tool;
- run `psql` from the DB server or the user's local machine;
- use a temporary Docker PostgreSQL client container if Docker is available.

For an existing production database, back up first. Then apply incremental scripts in this order:

1. `init/04-update-operation-log-types.sql`
2. `init/05-region-and-flow-update.sql`
3. `init/06-auth-login-security.sql`
4. `init/07-login-failure-notification.sql`
5. the production-safe structure-only part of `init/08-region-manager-location-amount-notify.sql`

Do not run `init/01`, `init/02`, `init/03`, or the seed-data section of `init/08` on an existing production database unless the user wants test data or a fresh reset.

For the latest version, also ensure `notification_type_check` includes `close` and `revoke_dispatch`.

Load detailed SQL guidance from `references/production-deploy.md` when the user needs exact commands or SQL blocks.

## Docker Deployment

For old deployments, clean only this project stack unless the user confirms broader cleanup:

- `docker compose --env-file .env.production -f docker-compose.prod.yml down`
- remove same-name containers only if compose cannot manage them: `tianyiting-backend`, `tianyiting-frontend`, `tianyiting-mobile`
- preserve `backend_uploads` by default because it may contain uploaded images, files, and survey report attachments
- use `docker image prune -f` only as optional space cleanup

Start production services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

## Verification

Verify in this order:

- backend logs show Nest started successfully;
- `frontend` and `uniapp` containers are up;
- backend responds at `http://SERVER_IP:BACKEND_PORT/api/v1`;
- admin frontend opens at `http://SERVER_IP:FRONTEND_PORT`;
- H5 opens at `http://SERVER_IP:UNIAPP_PORT`;
- business flows work: login, region configuration, Excel import, opportunity creation, region filtering, region manager visibility, Tianditu map selection, close/revoke notification history.

If an API returns `401`, treat it as proof the backend is reachable and auth is required. If it returns `500`, inspect backend logs and confirm database scripts were applied.
