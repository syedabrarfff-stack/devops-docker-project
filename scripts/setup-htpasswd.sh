#!/bin/bash
# Run this ONCE on the EC2 host before starting nginx.
# Creates /etc/nginx/.htpasswd for Control Room basic auth.
set -e

HTPASSWD_FILE="/etc/nginx/.htpasswd"

if [ -z "$CAPTAIN_USERNAME" ]; then
  CAPTAIN_USERNAME="captain"
fi

if [ -z "$CAPTAIN_PASSWORD" ]; then
  echo "ERROR: Set CAPTAIN_PASSWORD environment variable before running this script."
  exit 1
fi

echo "Creating nginx htpasswd for user: $CAPTAIN_USERNAME"

if ! command -v htpasswd &>/dev/null; then
  apt-get update -qq && apt-get install -y -qq apache2-utils
fi

htpasswd -cb "$HTPASSWD_FILE" "$CAPTAIN_USERNAME" "$CAPTAIN_PASSWORD"
chmod 600 "$HTPASSWD_FILE"

echo "✅ htpasswd created at $HTPASSWD_FILE"
echo "   User: $CAPTAIN_USERNAME"
echo "   Nginx can now serve the Control Room with basic auth."
