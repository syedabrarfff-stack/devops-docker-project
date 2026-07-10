#!/bin/bash
# EC2 deploy script — executed via SSM send-command (base64-encoded from GitHub Actions)
# __GHTOKEN__ is replaced by sed in the workflow before encoding.
set -e

# AWS-RunShellScript via SSM does not set $HOME the way an interactive SSH
# session does — `git config --global` and similar fail with
# "fatal: $HOME not set" without this. SSM commands run as root.
export HOME="${HOME:-/root}"

ACTION="${1:-full-restart}"
GH_TOKEN="__GHTOKEN__"

# ── Locate deploy directory ───────────────────────────────────────────────────
DEPLOY_DIR=/opt/jarvis
if [ ! -f /opt/jarvis/infrastructure/docker-compose.yml ]; then
  DEPLOY_DIR=/home/ubuntu/devops-docker-project
fi

# ── First-install: clone if docker-compose.yml is missing ────────────────────
if [ ! -f "$DEPLOY_DIR/infrastructure/docker-compose.yml" ]; then
  apt-get install -y git curl 2>/dev/null || true
  git clone "https://x-access-token:${GH_TOKEN}@github.com/syedabrarfff-stack/devops-docker-project.git" /opt/jarvis 2>&1 | tail -5
  DEPLOY_DIR=/opt/jarvis
fi

echo "=== DEPLOY DIR: $DEPLOY_DIR ==="
cd "$DEPLOY_DIR"

# ── Install docker-compose if missing ────────────────────────────────────────
which docker-compose 2>/dev/null || {
  curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
}

# ── Configure git credentials (ephemeral — removed at end) ───────────────────
git config --global credential.helper store
printf 'https://x-access-token:%s@github.com\n' "${GH_TOKEN}" > /root/.git-credentials
chmod 600 /root/.git-credentials
echo "Git credentials configured"

# ── Fetch + pull latest code ─────────────────────────────────────────────────
GIT_FETCH_OK=false
for i in 1 2 3 4 5; do
  git fetch origin claude/jarvis-cans-api-integration-ZThTD 2>&1 \
    && { GIT_FETCH_OK=true; break; } \
    || { echo "git fetch attempt $i/5 failed"; sleep 20; }
done
if [ "$GIT_FETCH_OK" != "true" ]; then
  echo "ERROR: All git fetch attempts failed — aborting"
  exit 1
fi

git checkout claude/jarvis-cans-api-integration-ZThTD 2>/dev/null || true
git clean -f -- public-site/ 2>/dev/null || true

for i in 1 2 3 4 5; do
  git pull origin claude/jarvis-cans-api-integration-ZThTD 2>&1 \
    && break \
    || { echo "git pull attempt $i/5 failed"; sleep 20; }
done
echo "=== LATEST: $(git log --oneline -1) ==="

# ── Ensure .env exists ───────────────────────────────────────────────────────
if [ ! -f "$DEPLOY_DIR/.env" ]; then
  cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
  echo "Created .env from .env.example"
fi

# ── Fix placeholder passwords (docker-compose uses :? operator — hard-fails) ─
if grep -qE "REPLACE_WITH_STRONG_DB_PASSWORD|REPLACE_WITH_STRONG_REDIS_PASSWORD|change-this-to-a-long-random-secret-key" \
    "$DEPLOY_DIR/.env" 2>/dev/null; then
  echo "=== Generating random passwords to replace placeholders ==="
  DB_PASS=$(openssl rand -hex 32)
  REDIS_PASS=$(openssl rand -hex 24)
  SECRET_KEY=$(openssl rand -hex 64)
  sed -i "s|REPLACE_WITH_STRONG_DB_PASSWORD|${DB_PASS}|g"             "$DEPLOY_DIR/.env"
  sed -i "s|REPLACE_WITH_STRONG_REDIS_PASSWORD|${REDIS_PASS}|g"       "$DEPLOY_DIR/.env"
  sed -i "s|change-this-to-a-long-random-secret-key|${SECRET_KEY}|g"  "$DEPLOY_DIR/.env"
  sed -i "s|change-this-to-a-strong-password|JarvisAdmin2025!|g"      "$DEPLOY_DIR/.env"
  echo "=== Passwords generated and saved ==="
fi

mkdir -p "$DEPLOY_DIR/jarvis-data/daily" "$DEPLOY_DIR/jarvis-data/outputs"

# ── P0-1: Enforce DEBUG=false — never runs in debug mode on EC2 ──────────────
sed -i 's/^DEBUG=.*/DEBUG=false/' "$DEPLOY_DIR/.env"
echo "=== DEBUG=false enforced in .env ==="

# ── P0-3: SSL certificate via certbot ────────────────────────────────────────
if [ "$ACTION" = "full-restart" ]; then
  DOMAIN="${SSL_DOMAIN:-aliyarsolutions.com}"
  CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  if ! command -v certbot &>/dev/null; then
    echo "=== Installing certbot ==="
    apt-get install -y certbot 2>/dev/null || snap install --classic certbot 2>/dev/null || true
  fi
  if command -v certbot &>/dev/null; then
    if [ ! -f "$CERT_PATH" ]; then
      echo "=== Requesting SSL cert for $DOMAIN ==="
      certbot certonly --standalone --non-interactive --agree-tos \
        -m "${ADMIN_EMAIL:-admin@aliyarsolutions.com}" \
        -d "$DOMAIN" -d "www.$DOMAIN" \
        --pre-hook  "docker stop jarvis_nginx 2>/dev/null || true" \
        --post-hook "cd /opt/jarvis/infrastructure && docker-compose -p jarvis start nginx 2>/dev/null || true" \
        2>&1 | tail -20
      echo "=== SSL cert requested for $DOMAIN ==="
    else
      certbot renew --quiet \
        --deploy-hook "docker exec jarvis_nginx nginx -s reload 2>/dev/null || true" \
        2>&1 | tail -5
      echo "=== SSL cert renewal checked for $DOMAIN ==="
    fi
  else
    echo "=== WARNING: certbot not available — SSL not configured ==="
  fi
fi

# ── Execute the requested action ─────────────────────────────────────────────
case "$ACTION" in

  nginx-reload)
    cd "$DEPLOY_DIR/infrastructure"
    docker-compose -p jarvis exec -T nginx nginx -s reload 2>/dev/null \
      || docker-compose -p jarvis restart nginx
    curl -sf http://localhost/health && echo HEALTH_OK || echo HEALTH_FAIL
    ;;

  git-pull-only)
    echo "=== GIT PULL COMPLETE ==="
    git log --oneline -3
    ;;

  frontend-only)
    cd "$DEPLOY_DIR/infrastructure"
    docker-compose -p jarvis build --no-cache frontend > /tmp/frontend_build.log 2>&1 \
      && echo FRONTEND_BUILD_OK || echo FRONTEND_BUILD_FAILED
    tail -15 /tmp/frontend_build.log
    docker-compose -p jarvis up -d --no-deps frontend 2>&1 | tail -3
    sleep 5
    curl -sf http://localhost/health && echo NGINX_PROXY_OK || echo NGINX_PROXY_FAIL
    docker-compose -p jarvis ps frontend
    ;;

  backend-only)
    cd "$DEPLOY_DIR/infrastructure"
    docker stop jarvis_backend 2>/dev/null || true
    docker rm jarvis_backend 2>/dev/null || true
    fuser -k 8000/tcp 2>/dev/null || true
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    sleep 2
    docker-compose -p jarvis up -d --no-deps --build backend 2>&1 | tail -5
    sleep 20
    docker-compose -p jarvis exec -T backend alembic upgrade head 2>&1 | tail -10 \
      || echo MIGRATION_ATTEMPTED
    sleep 5
    curl -sf http://localhost:8000/health && echo BACKEND_HEALTHY || echo BACKEND_FAIL
    docker-compose -p jarvis ps
    ;;

  verify-status)
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    curl -sf http://localhost/health && echo NGINX_PROXY_OK || echo NGINX_PROXY_FAIL
    curl -sf http://localhost:8000/health && echo BACKEND_OK || echo BACKEND_DOWN
    docker exec jarvis_backend alembic current 2>/dev/null || true
    ;;

  set-captain-credentials)
    # Fixes login by forcing CAPTAIN_USERNAME/PASSWORD in .env and regenerating
    # nginx basic-auth .htpasswd to match — both are gitignored secrets that only
    # ever existed in a local sandbox, never reached this server until now.
    # NEW_USER / NEW_PASS must be supplied via env vars at invocation time —
    # never hardcode credentials in this script, it is committed to git.
    NEW_USER="${CAPTAIN_USERNAME_OVERRIDE:?CAPTAIN_USERNAME_OVERRIDE must be set}"
    NEW_PASS="${CAPTAIN_PASSWORD_OVERRIDE:?CAPTAIN_PASSWORD_OVERRIDE must be set}"

    if grep -q "^CAPTAIN_USERNAME=" "$DEPLOY_DIR/.env"; then
      sed -i "s|^CAPTAIN_USERNAME=.*|CAPTAIN_USERNAME=${NEW_USER}|" "$DEPLOY_DIR/.env"
    else
      echo "CAPTAIN_USERNAME=${NEW_USER}" >> "$DEPLOY_DIR/.env"
    fi
    if grep -q "^CAPTAIN_PASSWORD=" "$DEPLOY_DIR/.env"; then
      sed -i "s|^CAPTAIN_PASSWORD=.*|CAPTAIN_PASSWORD=${NEW_PASS}|" "$DEPLOY_DIR/.env"
    else
      echo "CAPTAIN_PASSWORD=${NEW_PASS}" >> "$DEPLOY_DIR/.env"
    fi
    echo "=== .env CAPTAIN credentials set ==="

    # Regenerate nginx basic-auth file (bcrypt via openssl, no extra deps needed)
    HTPASSWD_FILE="$DEPLOY_DIR/infrastructure/nginx/.htpasswd"
    HASH=$(openssl passwd -apr1 "${NEW_PASS}")
    echo "${NEW_USER}:${HASH}" > "$HTPASSWD_FILE"
    echo "=== nginx .htpasswd regenerated for user '${NEW_USER}' ==="

    cd "$DEPLOY_DIR/infrastructure"
    docker-compose -p jarvis up -d --no-deps --force-recreate backend nginx 2>&1 | tail -10
    sleep 15

    echo "=== VERIFYING LOGIN ==="
    LOGIN_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"${NEW_USER}\",\"password\":\"${NEW_PASS}\"}")
    if [ "$LOGIN_RESP" = "200" ]; then
      echo "LOGIN_VERIFIED_OK (HTTP $LOGIN_RESP)"
    else
      echo "LOGIN_VERIFY_FAILED (HTTP $LOGIN_RESP)"
    fi
    curl -sf http://localhost/health && echo NGINX_PROXY_OK || echo NGINX_PROXY_FAIL
    ;;

  *)
    # full-restart
    cd "$DEPLOY_DIR/infrastructure"

    echo "=== CLEARING STALE CONTAINERS ==="
    docker stop jarvis_backend jarvis_nginx 2>/dev/null || true
    docker rm jarvis_backend jarvis_nginx 2>/dev/null || true
    docker ps -q --filter publish=8000 | xargs -r docker stop 2>/dev/null || true
    docker ps -aq --filter publish=8000 | xargs -r docker rm 2>/dev/null || true

    echo "=== STARTING DEPS (postgres + redis) ==="
    docker-compose -p jarvis up -d postgres redis 2>&1 | tail -3
    sleep 15

    echo "=== CLEARING PYCACHE ==="
    find "$DEPLOY_DIR/backend" -type d -name __pycache__ | xargs -r rm -rf 2>/dev/null || true
    find "$DEPLOY_DIR/backend" -name '*.pyc' | xargs -r rm -f 2>/dev/null || true

    echo "=== REBUILDING BACKEND ==="
    if docker-compose -p jarvis build --no-cache backend > /tmp/build.log 2>&1; then
      echo BUILD_OK
      tail -30 /tmp/build.log
    else
      echo BUILD_FAILED
      tail -30 /tmp/build.log
      exit 1
    fi

    echo "=== RELEASING PORT 8000 ==="
    fuser -k 8000/tcp 2>/dev/null || true
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    sleep 3

    docker-compose -p jarvis up -d --no-deps backend 2>&1 | tail -3

    echo "=== REBUILDING NGINX ==="
    docker-compose -p jarvis up -d --no-deps --build nginx 2>&1 | tail -3

    echo "=== REBUILDING FRONTEND ==="
    docker-compose -p jarvis build --no-cache frontend > /tmp/frontend_build.log 2>&1 \
      && echo FRONTEND_BUILD_OK || echo FRONTEND_BUILD_WARN
    tail -10 /tmp/frontend_build.log
    docker-compose -p jarvis up -d --no-deps frontend 2>&1 | tail -3

    echo "=== WAITING FOR BACKEND STARTUP (45s) ==="
    sleep 45

    echo "=== BACKEND CONTAINER STATUS ==="
    docker inspect jarvis_backend --format='{{.State.Status}}' 2>/dev/null || echo no_container

    echo "=== RUNNING ALEMBIC MIGRATIONS ==="
    docker-compose -p jarvis exec -T backend alembic upgrade head 2>&1 | tail -10 \
      || docker exec jarvis_backend alembic upgrade head 2>&1 | tail -10 \
      || echo MIGRATION_ATTEMPTED

    sleep 5

    echo "=== HEALTH CHECKS ==="
    curl -sf http://localhost/health && echo NGINX_PROXY_HEALTH_OK || echo NGINX_PROXY_HEALTH_FAIL
    curl -sf http://localhost:8000/health && echo BACKEND_HEALTH_OK || echo BACKEND_HEALTH_FAIL

    echo "=== BACKEND LOGS TAIL ==="
    docker logs jarvis_backend --tail=30 2>&1 | tail -30

    echo "=== TRIGGERING PIPELINE ==="
    curl -sf -X POST "http://localhost:8000/api/v1/leads/bulk-discover?limit=200" \
      && echo BULK_DISCOVER_TRIGGERED || echo BULK_DISCOVER_FAIL
    curl -sf -X POST "http://localhost:8000/api/v1/crm/hubspot-sync" \
      && echo HUBSPOT_SYNC_TRIGGERED || echo HUBSPOT_SYNC_FAIL

    WA=$(curl -sf http://localhost:8080/instance/connectionState/jarvis-main \
      -H "apikey: jarvis-master-key" 2>/dev/null || echo "{}")
    echo "WhatsApp state: $WA"

    echo "=== DOCKER STATUS ==="
    docker-compose -p jarvis ps

    echo "=== DEPLOY_COMPLETE ==="
    ;;
esac

# Clean up ephemeral git credentials
rm -f /root/.git-credentials
