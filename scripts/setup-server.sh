#!/bin/bash
# ==================================================
# Hetzner Server Initial Setup
# Run once on a fresh Ubuntu 24.04 LTS server
# Usage: bash setup-server.sh your-domain.ch
# ==================================================

set -euo pipefail

DOMAIN="${1:-immo.example.ch}"
APP_USER="immo"
APP_DIR="/opt/immo"

echo "==== ImmoManager Server Setup ===="
echo "Domain: $DOMAIN"
echo ""

# --- System updates ---
apt-get update && apt-get upgrade -y
apt-get install -y curl git ufw fail2ban unattended-upgrades

# --- Docker ---
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# --- Firewall ---
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# --- fail2ban (brute-force protection) ---
systemctl enable fail2ban
systemctl start fail2ban

# --- App user ---
useradd -m -s /bin/bash "$APP_USER" || true
usermod -aG docker "$APP_USER"

# --- App directory ---
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# --- SSL certificate (initial) ---
docker run --rm \
  -v /opt/immo/certbot/webroot:/var/www/certbot \
  -v /opt/immo/certbot/certs:/etc/letsencrypt \
  certbot/certbot certonly \
    --webroot -w /var/www/certbot \
    --non-interactive --agree-tos \
    -m "admin@${DOMAIN}" \
    -d "$DOMAIN" \
    -d "www.${DOMAIN}" || echo "SSL: Skipped (DNS not yet pointing here)"

# --- Automatic backups via cron ---
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/immo/scripts/backup.sh >> /var/log/immo-backup.log 2>&1") | crontab -

# --- Automatic security updates ---
cat > /etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo ""
echo "==== Setup complete ===="
echo ""
echo "Next steps:"
echo "  1. Point DNS A-record for $DOMAIN → $(curl -s ifconfig.me)"
echo "  2. cd $APP_DIR && git clone <your-repo> ."
echo "  3. cp .env.example .env && nano .env"
echo "  4. bash scripts/deploy.sh"
