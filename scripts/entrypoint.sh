#!/bin/sh
set -eu

if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    python - <<'PY'
import os
import secrets
from pathlib import Path

key_file = Path(os.environ["DJANGO_DATA_DIR"]) / "secret-key"
os.umask(0o077)
try:
    with key_file.open("x", encoding="ascii") as output:
        output.write(secrets.token_urlsafe(64) + "\n")
except FileExistsError:
    pass
PY
fi

if [ "${1:-}" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py seed_demo
fi

exec "$@"
