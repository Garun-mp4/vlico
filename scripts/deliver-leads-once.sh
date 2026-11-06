#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE=${VLICO_ENV_FILE:-"$APP_ROOT/.env"}
set -a
. "$ENV_FILE"
set +a
exec "$APP_ROOT/.venv/bin/python" "$APP_ROOT/backend/manage.py" deliver_leads --once
