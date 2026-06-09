#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

cd "${ROOT_DIR}/backend"
DJANGO_SETTINGS_MODULE=config.settings.test ./.venv/bin/python manage.py migrate --noinput
DJANGO_SETTINGS_MODULE=config.settings.test ./.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload &
BACKEND_PID=$!

for _ in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8000/api/health/ >/dev/null; then
    break
  fi
  sleep 1
done

curl --silent --fail http://127.0.0.1:8000/api/health/ >/dev/null
cd "${ROOT_DIR}/frontend"
npm run test:e2e:full-stack
