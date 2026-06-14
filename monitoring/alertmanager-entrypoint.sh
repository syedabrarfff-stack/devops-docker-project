#!/bin/sh
# Substitute environment variables into alertmanager config at container start
# This allows secrets to be injected via Docker environment without being committed
set -e

CFG_TEMPLATE="/etc/alertmanager/alertmanager.yml"
CFG_RUNTIME="/tmp/alertmanager-runtime.yml"

# envsubst replaces ${SLACK_WEBHOOK_URL} and any other ${VAR} references
envsubst < "$CFG_TEMPLATE" > "$CFG_RUNTIME"

exec /bin/alertmanager \
  --config.file="$CFG_RUNTIME" \
  --storage.path=/alertmanager \
  "$@"
