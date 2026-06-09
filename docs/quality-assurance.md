# Quality Assurance

## Automated Checks

Backend quality gates:

- 59 Django tests covering authentication, permissions, validation, execution state, scheduling, retry exhaustion, analytics, media cleanup, WebSockets, and AI-agent workflows
- minimum 80% coverage enforced by `.coveragerc`
- Django production deployment security check
- migration drift check
- `pip-audit` dependency vulnerability scan

Frontend quality gates:

- ESLint
- Vitest and React Testing Library component/API tests
- Playwright end-to-end workflow covering login, analytics, and scheduled execution creation
- Real-stack Playwright workflow covering registration, project/test-case creation, scheduling, the Python browser executor, persisted results, and execution-detail review
- Vite production build
- `npm audit` dependency vulnerability scan

## Security Testing

Security tests verify unauthenticated request rejection, role escalation prevention, object-level access control, hidden-project isolation, analytics isolation, and scheduled-execution ownership. CI also audits Python and Node dependencies on every change. Dependabot checks Python, Node, and GitHub Actions dependencies weekly.

## Resolved Issues

- Replaced the silent in-process thread fallback for Celery broker failures with explicit failed execution state, error logs, reports, API `503` responses, and Celery retry behaviour.
- Added a database index for due scheduled-execution queries and guarded dispatch with a row lock to prevent duplicate dispatch.
- Upgraded vulnerable React Router, Django, PyJWT, Twisted, pytest, idna, Pygments, and ujson versions after dependency audits identified published vulnerabilities.
- Added frontend component and end-to-end testing after the original implementation relied only on lint and build checks.

## Local Verification

```bash
cd backend
./.venv/bin/coverage run manage.py test --settings=config.settings.test
./.venv/bin/coverage report
./.venv/bin/pip-audit -r requirements.txt

cd ../frontend
npm run lint
npm run test
npm run test:e2e
npm run test:e2e:full-stack
npm run build
npm audit --audit-level=high --registry=https://registry.npmjs.org
```
