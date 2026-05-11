#!/usr/bin/env bash
# DigitalOcean App Platform: ensures gunicorn gets WSGI module and binds to $PORT.
set -euo pipefail
cd "$(dirname "$0")/.."

python manage.py migrate
python manage.py collectstatic --noinput

# App Platform sets PORT (health checks hit this port, often 8080).
export PORT="${PORT:-8080}"

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120
