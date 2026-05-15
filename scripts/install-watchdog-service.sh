#!/bin/bash
# Install JARVIS Watchdog as a systemd service so it starts on boot
# Run as: sudo bash scripts/install-watchdog-service.sh

set -e

DEPLOY_DIR="/home/ubuntu/devops-docker-project"
SERVICE_FILE="/etc/systemd/system/jarvis-watchdog.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=JARVIS Watchdog — keeps all containers alive 24/7
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$DEPLOY_DIR
ExecStart=/bin/bash $DEPLOY_DIR/scripts/watchdog.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=SLACK_WEBHOOK=${SLACK_WEBHOOK:-}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jarvis-watchdog
systemctl start jarvis-watchdog

echo "✅ JARVIS Watchdog installed and started"
echo "   Check status: systemctl status jarvis-watchdog"
echo "   View logs:    journalctl -u jarvis-watchdog -f"
