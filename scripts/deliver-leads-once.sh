#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
set -a
. "$APP_ROOT/.env"
set +a
exec "$APP_ROOT/.venv/bin/python" "$APP_ROOT/backend/manage.py" deliver_leads --once
