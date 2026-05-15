#!/bin/bash
set -euo pipefail

install -m 755 /home/ubuntu/bunny-production/scripts/watchdog.sh /usr/local/bin/jarvis-watchdog

cat >/etc/systemd/system/jarvis-watchdog.service <<'EOF'
[Unit]
Description=JARVIS container watchdog
After=docker.service
Requires=docker.service

[Service]
Type=simple
Environment=COMPOSE_FILE=/home/ubuntu/bunny-production/infrastructure/docker-compose.yml
ExecStart=/usr/local/bin/jarvis-watchdog
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now jarvis-watchdog.service
systemctl status jarvis-watchdog.service --no-pager
