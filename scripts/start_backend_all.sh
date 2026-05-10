#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${DJANGO_SETTINGS_MODULE:=config.settings.local}"
export DJANGO_SETTINGS_MODULE

cleanup() {
  echo
  echo "Stopping backend processes..."
  jobs -p | xargs -r kill
}
trap cleanup EXIT INT TERM

echo "Using DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

echo "Starting Django runserver..."
uv run python manage.py runserver 0.0.0.0:8000 &

# Give web process a moment to initialize before workers.
sleep 1

echo "Starting Celery worker..."
uv run celery -A config worker -l info &

echo "Starting Celery beat..."
uv run celery -A config beat -l info &

echo "Starting Alpaca news stream daemon..."
uv run python manage.py run_news_stream &

echo "All backend processes started. Press Ctrl+C to stop all."
wait
