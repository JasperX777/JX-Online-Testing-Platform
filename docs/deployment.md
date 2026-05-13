# Deployment Guide

## Deployment Topology

The production stack contains:

- `nginx`: public entrypoint for frontend traffic, API requests, WebSocket connections, static files, and media files
- `frontend`: compiled React application served as static assets
- `backend`: Django application served through Daphne
- `worker`: Celery worker for background execution tasks
- `db`: PostgreSQL
- `redis`: Celery broker and Channels backend

## Files

- Local or pre-production stack: [compose.yaml](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/compose.yaml)
- Production stack: [compose.prod.yaml](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/compose.prod.yaml)
- Reverse proxy config: [docker/nginx/default.conf](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/docker/nginx/default.conf)
- Environment template: [.env.example](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/.env.example)

## Local Validation

```bash
cd /Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Validation targets:

- `http://localhost/` serves the frontend
- `http://localhost/api/health/` returns `{"status":"OK"}`
- `docker compose logs backend`
- `docker compose logs worker`

## Production Preparation

Recommended prerequisites:

- a Linux host
- Docker Engine
- Docker Compose plugin
- a domain name
- ports `80` and `443` available for public traffic

Suggested server directory:

```text
/opt/jx-online-testing-platform/
├── compose.prod.yaml
├── .env
└── docker/nginx/default.conf
```

## Required Environment Variables

At minimum, configure:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CHANNEL_REDIS_URL`
- `BACKEND_IMAGE`
- `FRONTEND_IMAGE`

Recommended production values:

- `DJANGO_SECURE_SSL_REDIRECT=true`
- `DJANGO_SESSION_COOKIE_SECURE=true`
- `DJANGO_CSRF_COOKIE_SECURE=true`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`

## CI/CD Workflow

### CI

[.github/workflows/ci.yml](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/.github/workflows/ci.yml) runs on push and pull request and validates:

- backend dependency installation
- Django tests
- production configuration checks
- frontend dependency installation
- ESLint
- Vite production build

### CD

[.github/workflows/deploy.yml](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/.github/workflows/deploy.yml) can:

1. build backend and frontend images
2. publish images to GHCR
3. copy deployment files to the target server
4. update the running stack over SSH with Docker Compose

## GitHub Secrets

The deployment workflow expects:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_PATH`

If the server needs to pull private GHCR images, also configure:

- `GHCR_USER`
- `GHCR_PAT`

## Recommended Rollout Steps

1. Configure repository secrets in GitHub.
2. Prepare the target server and write a production `.env`.
3. Run the stack manually once with `docker compose -f compose.prod.yaml up -d`.
4. Enable automated rollout from the default branch after the first successful manual verification.
