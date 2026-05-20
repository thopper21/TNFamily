#!/bin/sh
set -e
flask db upgrade
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 8 --timeout 0 run:app
