#!/usr/bin/env bash
# Backup SQLite jobs.db (run via cron on host or Railway scheduled task).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${DATABASE_URL:-$ROOT/jobs.db}"
DB="${DB#sqlite:///}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$OUT_DIR"
if [[ ! -f "$DB" ]]; then
  echo "Database not found: $DB" >&2
  exit 1
fi
sqlite3 "$DB" ".backup '$OUT_DIR/jobs-$STAMP.db'"
echo "Wrote $OUT_DIR/jobs-$STAMP.db"
# Keep last 14 backups
ls -1t "$OUT_DIR"/jobs-*.db 2>/dev/null | tail -n +15 | xargs -r rm -f
