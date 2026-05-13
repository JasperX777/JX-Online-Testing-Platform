# Frontend Technical Documentation

## Stack

- React 19
- React Router 7
- Vite 8
- ESLint 9

## Responsibilities

The frontend is responsible for:

- authentication flows and token-aware session handling
- project, test case, and execution views
- communication with backend REST endpoints through `/api`
- live execution updates through `/ws`

## Directory Overview

```text
src/
├── components/   # Shared UI components and layout shell
├── contexts/     # Authentication context
├── lib/          # API client and token storage
└── pages/        # Route-level screens
```

## Runtime Model

- In development, the app is served by Vite.
- `vite.config.js` proxies `/api`, `/ws`, and `/media` to Django.
- In production, the frontend is built into static assets and served by an Nginx container.
- External traffic is routed through the top-level Nginx reverse proxy shared with the backend.

## API Access Pattern

[src/lib/api.js](/Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/frontend/src/lib/api.js) provides a unified request layer that:

- attaches the current JWT access token automatically
- retries once after refreshing the access token on `401`
- normalizes JSON and error handling

Because production traffic is routed through one domain and one Nginx entrypoint, the frontend does not need a separate API base URL for deployment.

## Build And Quality

```bash
cd /Users/jasperxue/PycharmProjects/JX-Online-Testing-Platform/frontend
npm ci
npm run lint
npm run build
```

CI currently runs:

- `npm run lint`
- `npm run build`

## Containerization

- Build stage: `node:22-alpine`
- Runtime stage: `nginx:1.27-alpine`
- SPA refresh support: `try_files $uri $uri/ /index.html`

## Follow-Up

- The frontend currently has lint and build validation, but no unit test suite yet.
- If you want stronger UI quality gates later, `Vitest` and `React Testing Library` would be the natural next step.
