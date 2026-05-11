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

echo "Applying database migrations..."
uv run python manage.py migrate --noinput

echo "Starting ASGI server (Daphne)..."
uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application &
DAPHNE_PID=$!

# Fail fast if ASGI startup crashed (e.g., import/config errors).
sleep 1
if ! kill -0 "$DAPHNE_PID" 2>/dev/null; then
  echo "Daphne failed to start. Exiting."
  exit 1
fi

# Give web process a moment to initialize before workers.
sleep 1

echo "Starting Celery worker..."
uv run celery -A config worker -l info &

echo "Starting Celery beat..."
uv run celery -A config beat -l info &

echo "Starting Alpaca news stream daemon..."
uv run python manage.py run_news_stream &

echo "Starting Alpaca market trade stream daemon..."
uv run python manage.py run_alpaca_stream &

echo "All backend processes started. Press Ctrl+C to stop all."
wait
