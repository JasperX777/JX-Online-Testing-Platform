# Backend Technical Documentation

## Stack

- Django 6
- Django REST Framework
- Channels
- Celery
- PostgreSQL
- Redis
- Playwright Python

## Responsibilities

The backend is responsible for:

- authentication and current-user APIs
- project management and access control
- test case storage and validation
- execution tracking, logs, reports, screenshots, and video metadata
- WebSocket event broadcasting for live execution updates
- asynchronous execution dispatch through Celery workers
- scheduled execution dispatch through Celery beat
- permission-scoped execution analytics
- persistent dispatch-failure reporting and Celery task retries

## Settings Model

The backend currently provides three settings modules:

- `config.settings.dev`: development mode, supports PostgreSQL or SQLite
- `config.settings.test`: CI and test mode, uses SQLite, in-memory channels, and eager Celery
- `config.settings.prod`: production mode, enables security settings and connects to PostgreSQL and Redis

Entrypoints:

- [manage.py](manage.py)
- [config/asgi.py](config/asgi.py)
- [config/celery.py](config/celery.py)

All of them support environment-based switching through `DJANGO_SETTINGS_MODULE`.

## Core Modules

- `accounts/`: authentication, registration, and current-user data
- `projects/`: projects and project membership
- `testcases/`: structured test case definitions
- `executions/`: execution state, logs, reports, and live broadcasting

## API And Realtime

[config/urls.py](config/urls.py) exposes:

- `/api/auth/*` for authentication
- `/api/projects/*` for project resources
- `/api/testcases/*` for test case resources
- `/api/executions/*` for execution resources
- `/api/execution-schedules/*` for scheduled execution resources
- `/api/executions/analytics/` for seven-day execution statistics
- `/api/health/` for health monitoring

Realtime execution updates are delivered through Channels with Redis as the channel layer backend.

## Execution Runtime

The execution flow is:

1. Create a `TestExecution` record.
2. Build a step snapshot with `initialize_execution()`.
3. Dispatch background work through `run_test_execution_task`.
4. Run browser actions through Playwright in `execute_steps()`.
5. Persist logs, results, report data, screenshots, and video paths.
6. Broadcast progress and completion events over WebSocket.

Because the execution pipeline depends on Playwright, the production backend image installs browser binaries explicitly.

## Static And Media

- `STATIC_ROOT=/app/staticfiles`
- `MEDIA_ROOT=/app/media`

In production these directories are mounted into Nginx so that static files and execution artifacts remain available outside the application container.

## Quality Gates

```bash
cd backend
./.venv/bin/python manage.py test --settings=config.settings.test
./.venv/bin/python manage.py check --deploy --fail-level WARNING --settings=config.settings.prod
```

CI currently enforces:

- Django test execution with a minimum 80% backend coverage threshold
- production configuration checks
- Python dependency vulnerability auditing
