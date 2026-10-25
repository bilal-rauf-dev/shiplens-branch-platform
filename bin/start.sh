#!/bin/sh
set -e

# Explicit commands (such as id -u) can run without application startup or a database.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput
python manage.py createcachetable

if [ "${DEMO_MODE:-false}" = "true" ] && python manage.py help seed_demo >/dev/null 2>&1; then
    python manage.py seed_demo --if-empty
fi

exec gunicorn config.wsgi \
    --no-control-socket \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 60 \
    --max-requests 500 \
    --access-logfile -
