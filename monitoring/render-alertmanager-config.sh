#!/bin/sh
# Renders monitoring/alertmanager.yml (template, checked into git) into
# monitoring/alertmanager.rendered.yml (gitignored, contains the real
# SLACK_WEBHOOK_URL) using envsubst on the host.
#
# Alertmanager's own container image has no envsubst/package manager, so it
# cannot substitute ${SLACK_WEBHOOK_URL} itself — the substitution must
# happen before the file is bind-mounted in. Runs as ExecStartPre in
# jarvis-stable.service so it's always fresh before the stack starts.
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${JARVIS_ENV_FILE:-/opt/jarvis/.env}"
TEMPLATE="$REPO_ROOT/monitoring/alertmanager.yml"
RENDERED="$REPO_ROOT/monitoring/alertmanager.rendered.yml"

SLACK_WEBHOOK_URL=$(grep "^SLACK_WEBHOOK_URL=" "$ENV_FILE" | head -1 | cut -d= -f2-)
export SLACK_WEBHOOK_URL

envsubst '${SLACK_WEBHOOK_URL}' < "$TEMPLATE" > "$RENDERED"
