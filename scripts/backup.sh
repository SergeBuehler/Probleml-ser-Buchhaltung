#!/bin/bash
# ==================================================
# PostgreSQL Backup Script
# Runs nightly via cron at 03:00
# Keeps 30 days of backups
# ==================================================

set -euo pipefail

APP_DIR="/opt/immo"
BACKUP_DIR="$APP_DIR/backups"
DATE=$(date +%Y-%m-%d_%H-%M)
RETENTION_DAYS=30

cd "$APP_DIR"
source .env

mkdir -p "$BACKUP_DIR"

echo "[$DATE] Starting backup..."

# Dump PostgreSQL
docker compose exec -T db pg_dump \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --clean \
  | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

echo "[$DATE] Database backup: db_${DATE}.sql.gz"

# Backup media files (receipts, documents)
tar -czf "$BACKUP_DIR/media_${DATE}.tar.gz" \
  -C "$APP_DIR" media/ 2>/dev/null || true

echo "[$DATE] Media backup: media_${DATE}.tar.gz"

# Delete backups older than retention period
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "[$DATE] Cleanup: removed backups older than ${RETENTION_DAYS} days"
echo "[$DATE] Backup complete."

# Optional: sync to Cloudflare R2 (uncomment if configured)
# rclone sync "$BACKUP_DIR" r2:immo-backups/$(hostname) --max-age ${RETENTION_DAYS}d
