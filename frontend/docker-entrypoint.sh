#!/bin/sh
# Substitute only BACKEND_HOST — leaves nginx vars ($host, $remote_addr, etc.) intact.
BACKEND_HOST="${BACKEND_HOST:-backend}"
export BACKEND_HOST
envsubst '${BACKEND_HOST}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
