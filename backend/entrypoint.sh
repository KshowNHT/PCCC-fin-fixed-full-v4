#!/bin/sh
set -eu
python -c 'from app.config import assert_production_secrets_are_safe; assert_production_secrets_are_safe()'
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 3000 --workers 1 --proxy-headers --forwarded-allow-ips=172.28.76.0/24 --timeout-keep-alive 5
