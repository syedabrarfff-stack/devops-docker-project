#!/bin/bash
# Install JARVIS systemd units on the production EC2 host.
# Run as root: sudo bash /opt/jarvis/scripts/install-systemd-units.sh
#
# Units installed:
#   jarvis-stable.service       — starts Docker Compose stack on boot
#   jarvis-backup.service/.timer — nightly PostgreSQL → S3 backup at 02:00 UTC
#   jarvis-health-check.service/.timer — health probe every 5 min

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/jarvis}"
SYSTEMD_DIR="/etc/systemd/system"

# Determine canonical unit source directory.
# jarvis-stable.service lives in infra/systemd/; the others are in infrastructure/systemd/.
INFRA_SYSTEMD="$DEPLOY_DIR/infrastructure/systemd"
CORE_SYSTEMD="$DEPLOY_DIR/infra/systemd"

install_unit() {
    local src="$1"
    local name
    name="$(basename "$src")"
    echo "  installing $name"
    cp "$src" "$SYSTEMD_DIR/$name"
}

echo "=== JARVIS systemd unit installation ==="
echo "Deploy dir: $DEPLOY_DIR"

# Core service (brings up the Docker Compose stack)
install_unit "$CORE_SYSTEMD/jarvis-stable.service"

# Backup service + timer
install_unit "$INFRA_SYSTEMD/jarvis-backup.service"
install_unit "$INFRA_SYSTEMD/jarvis-backup.timer"

# Health-check service + timer
install_unit "$INFRA_SYSTEMD/jarvis-health-check.service"
install_unit "$INFRA_SYSTEMD/jarvis-health-check.timer"

echo "=== Reloading systemd daemon ==="
systemctl daemon-reload

echo "=== Enabling units ==="
systemctl enable jarvis-stable.service
systemctl enable jarvis-backup.timer
systemctl enable jarvis-health-check.timer

echo "=== Starting timers (if not already active) ==="
systemctl start jarvis-backup.timer     || true
systemctl start jarvis-health-check.timer || true

# Start the main service only if Docker Compose stack is not already up.
if ! docker ps --filter "name=jarvis_backend" --format "{{.Names}}" | grep -q jarvis_backend 2>/dev/null; then
    echo "=== Starting jarvis-stable.service ==="
    systemctl start jarvis-stable.service
else
    echo "=== Docker stack already running — skipping jarvis-stable.service start ==="
fi

echo ""
echo "=== Installed units ==="
systemctl list-units --type=service --type=timer --no-pager | grep jarvis || true

echo ""
echo "Done. Units will persist across reboots."
