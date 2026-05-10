#!/bin/bash
# ==================================================
# ImmoManager — Deploy / Update Script
# Run on the Hetzner server to deploy or update
# Usage: bash scripts/deploy.sh
# ==================================================

set -euo pipefail

APP_DIR="/opt/immo"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

cd "$APP_DIR"

echo "==== ImmoManager Deploy ===="
date

# 1. Pull latest code
echo "→ Pulling latest code..."
git pull origin main

# 2. Load env (validate required vars)
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in values."
  exit 1
fi

source .env
: "${SECRET_KEY:?SECRET_KEY is required}"
: "${DOMAIN:?DOMAIN is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"

# 3. Build updated images
echo "→ Building Docker images..."
$COMPOSE build --pull --no-cache

# 4. Run migrations (zero-downtime: run before swapping containers)
echo "→ Running database migrations..."
$COMPOSE run --rm backend python manage.py migrate --noinput

# 5. Collect static files
echo "→ Collecting static files..."
$COMPOSE run --rm backend python manage.py collectstatic --noinput

# 6. Restart services (rolling: DB and Redis stay up)
echo "→ Restarting services..."
$COMPOSE up -d --remove-orphans

# 7. Wait for backend health
echo "→ Waiting for backend..."
sleep 5
for i in {1..12}; do
  if $COMPOSE exec -T backend python manage.py check --deploy 2>/dev/null; then
    echo "✓ Backend healthy"
    break
  fi
  sleep 5
done

# 8. Remove old images
echo "→ Cleaning up old images..."
docker image prune -f

echo ""
echo "==== Deploy complete ===="
echo "App running at: https://${DOMAIN}"
