#!/usr/bin/env bash
# Consistent backup: stop all application writers while capturing PostgreSQL + files.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
DEST="${1:-backups/$(date -u +%Y%m%dT%H%M%SZ)}"
if [ -e "$DEST/database.dump" ] || [ -e "$DEST/files.tar.gz" ]; then
  echo "Backup destination already contains a backup; choose a new directory." >&2
  exit 1
fi
mkdir -p "$DEST"
WAS_RUNNING="$(docker compose ps --status running --services backend)"
restart_backend() {
  if [ "$WAS_RUNNING" = "backend" ]; then docker compose start backend >/dev/null; fi
}
trap restart_backend EXIT
docker compose stop backend
docker compose exec -T postgres pg_dump -U pccc_app -d pccc_db -Fc > "$DEST/database.dump"
docker compose run --rm --no-deps --entrypoint tar backend -C /app/data -czf - . > "$DEST/files.tar.gz"
docker compose exec -T postgres pg_restore --list < "$DEST/database.dump" >/dev/null
tar -tzf "$DEST/files.tar.gz" >/dev/null
(cd "$DEST" && sha256sum database.dump files.tar.gz) > "$DEST/SHA256SUMS"
echo "Backup completed: $DEST. Test restoration in a separate environment."
