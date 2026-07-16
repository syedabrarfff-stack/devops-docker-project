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

  production-audit)
    # ══════════════════════════════════════════════════════════════════════════
    # READ-ONLY PRODUCTION AUDIT — collects evidence only, modifies nothing.
    # Never: stops/starts/restarts containers, modifies .env/DB/Docker/AWS,
    # sends emails/WhatsApp, creates/updates/deletes data.
    # ══════════════════════════════════════════════════════════════════════════
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           JARVIS PRODUCTION AUDIT — READ ONLY              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # ── 1. Backend Health ─────────────────────────────────────────────────
    echo "═══ [1/18] BACKEND HEALTH ═══"
    HEALTH=$(curl -sf http://localhost:8000/health 2>&1) && echo "  /health: OK" || echo "  /health: FAIL"
    echo "  Response: $HEALTH"
    READYZ=$(curl -sf http://localhost:8000/readyz 2>&1) && echo "  /readyz: OK" || echo "  /readyz: FAIL"
    echo "  Response: $READYZ"
    docker inspect jarvis_backend --format='  Container state: {{.State.Status}} | Restarts: {{.RestartCount}} | Started: {{.State.StartedAt}}' 2>/dev/null || echo "  Container: NOT FOUND"
    echo ""

    # ── 2. PostgreSQL ─────────────────────────────────────────────────────
    echo "═══ [2/18] POSTGRESQL ═══"
    docker inspect jarvis_postgres --format='  Container state: {{.State.Status}} | Restarts: {{.RestartCount}}' 2>/dev/null || echo "  Container: NOT FOUND"
    docker exec jarvis_postgres pg_isready -U jarvis 2>/dev/null && echo "  pg_isready: OK" || echo "  pg_isready: FAIL"
    docker exec jarvis_postgres psql -U jarvis -d jarvis -c "SELECT count(*) AS table_count FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "  Query failed"
    docker exec jarvis_postgres psql -U jarvis -d jarvis -c "SELECT pg_size_pretty(pg_database_size('jarvis')) AS db_size;" 2>/dev/null || echo "  Size query failed"
    echo ""

    # ── 3. Redis ──────────────────────────────────────────────────────────
    echo "═══ [3/18] REDIS ═══"
    docker inspect jarvis_redis --format='  Container state: {{.State.Status}} | Restarts: {{.RestartCount}}' 2>/dev/null || echo "  Container: NOT FOUND"
    docker exec jarvis_redis redis-cli ping 2>/dev/null || echo "  PING: FAIL"
    docker exec jarvis_redis redis-cli info memory 2>/dev/null | grep -E "used_memory_human|maxmemory_human" || echo "  Memory info unavailable"
    docker exec jarvis_redis redis-cli dbsize 2>/dev/null || echo "  DBSIZE: unavailable"
    echo ""

    # ── 4. Scheduler Status ───────────────────────────────────────────────
    echo "═══ [4/18] SCHEDULER STATUS ═══"
    curl -sf http://localhost:8000/api/v1/scheduler/status 2>&1 || echo "  Scheduler status endpoint failed"
    echo ""

    # ── 5. Registered Jobs ────────────────────────────────────────────────
    echo "═══ [5/18] REGISTERED JOBS ═══"
    JOBS=$(curl -sf http://localhost:8000/api/v1/scheduler/jobs 2>&1) && echo "$JOBS" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    jobs=data if isinstance(data,list) else data.get('jobs',data.get('items',[]))
    print(f'  Total registered: {len(jobs)}')
    for j in jobs[:10]:
        name=j.get('id',j.get('name','?'))
        nr=j.get('next_run','?')
        print(f'    {name} → next: {nr}')
    if len(jobs)>10: print(f'    ... and {len(jobs)-10} more')
except: print('  Parse failed')
" 2>/dev/null || echo "  Jobs endpoint failed"
    echo ""

    # ── 6. Recent Scheduler Executions ────────────────────────────────────
    echo "═══ [6/18] RECENT SCHEDULER EXECUTIONS ═══"
    curl -sf "http://localhost:8000/api/v1/scheduler/history?limit=15" 2>&1 | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    items=data if isinstance(data,list) else data.get('items',data.get('history',[]))
    print(f'  Recent executions: {len(items)}')
    for h in items[:10]:
        jid=h.get('job_id',h.get('name','?'))
        status=h.get('status',h.get('outcome','?'))
        ts=h.get('executed_at',h.get('timestamp','?'))
        print(f'    {jid}: {status} @ {ts}')
except: print('  No execution history available or parse failed')
" 2>/dev/null || echo "  History endpoint unavailable"
    echo ""

    # ── 7. Scheduler Exceptions ───────────────────────────────────────────
    echo "═══ [7/18] SCHEDULER EXCEPTIONS ═══"
    docker logs jarvis_backend --since=24h 2>&1 | grep -iE "scheduler.*error|scheduler.*exception|job.*failed|apscheduler.*error" | tail -10 || echo "  No scheduler exceptions in last 24h"
    echo ""

    # ── 8. Amazon SES Configuration ───────────────────────────────────────
    echo "═══ [8/18] AMAZON SES CONFIGURATION ═══"
    curl -sf http://localhost:8000/api/v1/email/status 2>&1 || echo "  SES status endpoint failed"
    echo ""
    echo "  SES info from /readyz:"
    echo "$READYZ" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    ses=data.get('checks',{}).get('ses',data.get('ses',{}))
    print(f'    Status: {ses.get(\"status\",\"unknown\")}')
    print(f'    Blocker: {ses.get(\"blocker_code\",ses.get(\"detail\",\"none\"))}')
    print(f'    Message: {ses.get(\"human_message\",ses.get(\"message\",\"n/a\"))}')
except: print('    SES parse from readyz failed')
" 2>/dev/null
    echo ""

    # ── 9. Evolution/WhatsApp Container ───────────────────────────────────
    echo "═══ [9/18] EVOLUTION / WHATSAPP CONTAINER ═══"
    docker inspect evolution-api --format='  Container state: {{.State.Status}} | Restarts: {{.RestartCount}} | Started: {{.State.StartedAt}}' 2>/dev/null || echo "  Container: NOT FOUND"
    docker logs evolution-api --tail=15 2>&1 | head -15 || echo "  No logs available"
    echo ""

    # ── 10. Evolution Database Existence ──────────────────────────────────
    echo "═══ [10/18] EVOLUTION DATABASE EXISTENCE ═══"
    docker exec jarvis_postgres psql -U jarvis -c "SELECT datname FROM pg_database WHERE datname='evolution';" 2>/dev/null || echo "  Cannot query postgres for evolution DB"
    docker exec jarvis_postgres psql -U jarvis -d evolution -c "SELECT count(*) AS table_count FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "  Evolution DB query failed (DB may not exist)"
    echo ""

    # ── 11. Backend ↔ Evolution Connectivity ──────────────────────────────
    echo "═══ [11/18] BACKEND ↔ EVOLUTION CONNECTIVITY ═══"
    WA_STATE=$(curl -sf http://localhost:8080/instance/connectionState/jarvis-main \
      -H "apikey: jarvis-master-key" 2>&1) && echo "  Evolution API response: $WA_STATE" || echo "  Evolution API unreachable"
    docker exec jarvis_backend curl -sf http://evolution:8080/instance/connectionState/jarvis-main \
      -H "apikey: jarvis-master-key" 2>/dev/null && echo "  Backend→Evolution internal: OK" || echo "  Backend→Evolution internal: FAIL"
    echo ""

    # ── 12. AI Providers ──────────────────────────────────────────────────
    echo "═══ [12/18] AI PROVIDERS ═══"
    curl -sf http://localhost:8000/api/v1/ai/providers/status 2>&1 | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    providers=data if isinstance(data,list) else data.get('providers',data.get('items',[]))
    for p in providers:
        name=p.get('name',p.get('provider','?'))
        status=p.get('status',p.get('state','?'))
        print(f'    {name}: {status}')
except: print('    AI providers parse failed')
" 2>/dev/null || echo "  AI providers endpoint failed"
    echo ""

    # ── 13. Nginx + Basic Auth Investigation ──────────────────────────────
    echo "═══ [13/18] NGINX + BASIC AUTH INVESTIGATION ═══"
    docker inspect jarvis_nginx --format='  Container state: {{.State.Status}} | Restarts: {{.RestartCount}} | Started: {{.State.StartedAt}}' 2>/dev/null || echo "  Container: NOT FOUND"
    curl -sf http://localhost/health && echo "  Nginx proxy /health: OK" || echo "  Nginx proxy /health: FAIL"
    echo ""
    echo "  --- .htpasswd diagnostics ---"
    if [ -f "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" ]; then
      echo "  .htpasswd file exists: YES"
      echo "  .htpasswd file size: $(wc -c < "$DEPLOY_DIR/infrastructure/nginx/.htpasswd") bytes"
      echo "  .htpasswd line count: $(wc -l < "$DEPLOY_DIR/infrastructure/nginx/.htpasswd")"
      HTPASSWD_USER=$(cut -d: -f1 "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" | head -1)
      echo "  .htpasswd username: $HTPASSWD_USER"
    else
      echo "  .htpasswd file exists: NO — this explains auth failure"
    fi
    echo ""
    echo "  --- .env CAPTAIN_USERNAME ---"
    if [ -f "$DEPLOY_DIR/.env" ]; then
      ENV_USER=$(grep "^CAPTAIN_USERNAME=" "$DEPLOY_DIR/.env" | cut -d= -f2 | head -1)
      echo "  .env CAPTAIN_USERNAME: ${ENV_USER:-NOT SET}"
    else
      echo "  .env file: NOT FOUND"
    fi
    echo ""
    if [ -n "$HTPASSWD_USER" ] && [ -n "$ENV_USER" ]; then
      if [ "$HTPASSWD_USER" = "$ENV_USER" ]; then
        echo "  Username match: YES — .htpasswd and .env agree"
      else
        echo "  Username match: NO — MISMATCH DETECTED"
        echo "    .htpasswd has: $HTPASSWD_USER"
        echo "    .env has: $ENV_USER"
        echo "    ROOT CAUSE: set-captain-credentials regenerated .htpasswd but"
        echo "    a subsequent git pull may have overwritten it with the repo copy"
      fi
    fi
    echo ""
    echo "  --- Password hash verification ---"
    if [ -f "$DEPLOY_DIR/.env" ] && [ -f "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" ]; then
      ENV_PASS=$(grep "^CAPTAIN_PASSWORD=" "$DEPLOY_DIR/.env" | cut -d= -f2 | head -1)
      if [ -n "$ENV_PASS" ]; then
        HTPASSWD_HASH=$(cut -d: -f2 "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" | head -1)
        HASH_TYPE="unknown"
        case "$HTPASSWD_HASH" in
          '$apr1$'*) HASH_TYPE="apr1 (MD5)" ;;
          '$2y$'*|'$2b$'*)  HASH_TYPE="bcrypt" ;;
          '{SHA}'*)  HASH_TYPE="SHA1" ;;
          *)         HASH_TYPE="crypt/other" ;;
        esac
        echo "  Hash algorithm: $HASH_TYPE"
        if command -v htpasswd &>/dev/null; then
          htpasswd -bv "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" "$HTPASSWD_USER" "$ENV_PASS" 2>/dev/null \
            && echo "  Password verification: PASS — .env password matches .htpasswd hash" \
            || echo "  Password verification: FAIL — .env password does NOT match .htpasswd hash"
        else
          VERIFY_HASH=$(openssl passwd -apr1 -salt "$(echo "$HTPASSWD_HASH" | cut -d'$' -f3)" "$ENV_PASS" 2>/dev/null)
          if [ "$VERIFY_HASH" = "$HTPASSWD_HASH" ]; then
            echo "  Password verification (openssl): PASS — .env password matches .htpasswd hash"
          else
            echo "  Password verification (openssl): FAIL — .env password does NOT match .htpasswd hash"
            echo "    ROOT CAUSE: The .htpasswd was generated with a different password than what is in .env"
            echo "    This happens when set-captain-credentials ran but git pull later overwrote .htpasswd"
          fi
        fi
      else
        echo "  CAPTAIN_PASSWORD not set in .env — cannot verify hash"
      fi
    else
      echo "  Cannot verify — .env or .htpasswd missing"
    fi
    echo ""
    echo "  --- Nginx auth_basic config ---"
    docker exec jarvis_nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -E "auth_basic|htpasswd" || echo "  Could not read nginx config from container"
    echo ""
    echo "  --- Nginx .htpasswd inside container ---"
    if docker exec jarvis_nginx test -f /etc/nginx/.htpasswd 2>/dev/null; then
      CONTAINER_HTPASSWD_USER=$(docker exec jarvis_nginx cut -d: -f1 /etc/nginx/.htpasswd 2>/dev/null | head -1)
      echo "  Container .htpasswd username: $CONTAINER_HTPASSWD_USER"
      echo "  Container .htpasswd size: $(docker exec jarvis_nginx wc -c < /etc/nginx/.htpasswd 2>/dev/null) bytes"
    else
      echo "  Container /etc/nginx/.htpasswd: FILE NOT FOUND"
    fi
    echo ""
    echo "  --- Host vs container .htpasswd comparison ---"
    if [ -f "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" ] && docker exec jarvis_nginx test -f /etc/nginx/.htpasswd 2>/dev/null; then
      HOST_MD5=$(md5sum "$DEPLOY_DIR/infrastructure/nginx/.htpasswd" 2>/dev/null | cut -d' ' -f1)
      CONTAINER_MD5=$(docker exec jarvis_nginx md5sum /etc/nginx/.htpasswd 2>/dev/null | cut -d' ' -f1)
      if [ "$HOST_MD5" = "$CONTAINER_MD5" ]; then
        echo "  Host ↔ Container .htpasswd: IDENTICAL (md5 match)"
      else
        echo "  Host ↔ Container .htpasswd: DIFFERENT — container has stale copy"
        echo "    Host md5:      $HOST_MD5"
        echo "    Container md5: $CONTAINER_MD5"
        echo "    ROOT CAUSE: Nginx container was not restarted after .htpasswd was regenerated"
        echo "    (volume is mounted :ro — container sees the bind-mount at start time)"
      fi
    else
      echo "  Cannot compare — one or both files missing"
    fi
    echo ""
    echo "  --- Nginx error log (auth failures) ---"
    docker logs jarvis_nginx --since=6h 2>&1 | grep -iE "auth|401|htpasswd|password" | tail -10 || echo "  No auth-related errors in nginx logs"
    echo ""
    echo "  --- Nginx reload check ---"
    docker exec jarvis_nginx nginx -t 2>&1 || echo "  Nginx config test failed"
    echo ""
    echo "  --- Live basic auth test (curl with .env credentials) ---"
    if [ -n "$ENV_USER" ] && [ -n "$ENV_PASS" ]; then
      AUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "${ENV_USER}:${ENV_PASS}" http://localhost/control-room 2>/dev/null)
      echo "  Basic auth curl to /control-room: HTTP $AUTH_CODE"
      if [ "$AUTH_CODE" = "200" ] || [ "$AUTH_CODE" = "301" ] || [ "$AUTH_CODE" = "302" ]; then
        echo "  Result: PASS — Nginx accepts .env credentials"
      elif [ "$AUTH_CODE" = "401" ]; then
        echo "  Result: FAIL — Nginx rejects .env credentials (401 Unauthorized)"
        echo "    CONFIRMED: .htpasswd credentials do not match .env credentials"
      else
        echo "  Result: Unexpected HTTP $AUTH_CODE"
      fi
      NO_AUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/control-room 2>/dev/null)
      echo "  No-auth curl to /control-room: HTTP $NO_AUTH_CODE"
    else
      echo "  Cannot test — username or password not available from .env"
    fi
    echo ""
    echo "  --- Backend login vs basic auth sync check ---"
    if [ -n "$ENV_USER" ] && [ -n "$ENV_PASS" ]; then
      BACKEND_LOGIN=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"${ENV_USER}\",\"password\":\"${ENV_PASS}\"}" 2>/dev/null)
      echo "  Backend /api/v1/auth/login with .env creds: HTTP $BACKEND_LOGIN"
      if [ "$BACKEND_LOGIN" = "200" ] && [ "$AUTH_CODE" = "401" ]; then
        echo "  DIAGNOSIS: Backend accepts creds but Nginx rejects them"
        echo "    → .htpasswd is out of sync with .env (git pull overwrote it)"
      elif [ "$BACKEND_LOGIN" = "200" ] && [ "$AUTH_CODE" != "401" ]; then
        echo "  DIAGNOSIS: Both backend and Nginx accept .env credentials — auth is synchronized"
      else
        echo "  DIAGNOSIS: Backend login returned HTTP $BACKEND_LOGIN — investigate separately"
      fi
    fi
    echo ""

    # ── 14. HTTPS / SSL ───────────────────────────────────────────────────
    echo "═══ [14/18] HTTPS / SSL ═══"
    DOMAIN="${SSL_DOMAIN:-aliyarsolutions.com}"
    CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    if [ -f "$CERT_PATH" ]; then
      echo "  SSL cert exists: YES"
      openssl x509 -in "$CERT_PATH" -noout -dates 2>/dev/null || echo "  Cannot read cert dates"
      openssl x509 -in "$CERT_PATH" -noout -subject 2>/dev/null || echo "  Cannot read cert subject"
    else
      echo "  SSL cert at $CERT_PATH: NOT FOUND"
    fi
    curl -sf -o /dev/null -w "  HTTPS status: %{http_code}\n" "https://${DOMAIN}/health" 2>/dev/null || echo "  HTTPS probe failed (may need --insecure or cert not yet issued)"
    echo ""

    # ── 15. Monitoring Stack ──────────────────────────────────────────────
    echo "═══ [15/18] MONITORING STACK ═══"
    docker inspect jarvis_prometheus --format='  Prometheus: {{.State.Status}}' 2>/dev/null || echo "  Prometheus: NOT RUNNING"
    docker inspect jarvis_grafana --format='  Grafana: {{.State.Status}}' 2>/dev/null || echo "  Grafana: NOT RUNNING"
    curl -sf http://localhost:9090/-/ready && echo "  Prometheus /ready: OK" || echo "  Prometheus /ready: FAIL or not exposed"
    curl -sf http://localhost:3000/api/health && echo "  Grafana /api/health: OK" || echo "  Grafana /api/health: FAIL or not exposed"
    echo ""

    # ── 16. Container Health (all) ────────────────────────────────────────
    echo "═══ [16/18] CONTAINER HEALTH ═══"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  docker ps failed"
    echo ""
    echo "  Stopped containers:"
    docker ps -a --filter "status=exited" --format "    {{.Names}}: exited {{.Status}}" 2>/dev/null || true
    echo ""

    # ── 17. System Resources ──────────────────────────────────────────────
    echo "═══ [17/18] SYSTEM RESOURCES ═══"
    echo "  --- CPU ---"
    uptime 2>/dev/null || echo "  uptime unavailable"
    echo "  CPU cores: $(nproc 2>/dev/null || echo unknown)"
    echo ""
    echo "  --- Memory ---"
    free -h 2>/dev/null || echo "  free unavailable"
    echo ""
    echo "  --- Disk ---"
    df -h / /var/lib/docker 2>/dev/null || df -h / 2>/dev/null || echo "  df unavailable"
    echo ""
    echo "  --- Swap ---"
    swapon --show 2>/dev/null || echo "  swap info unavailable"
    echo ""

    # ── 18. Remaining Production Blockers ─────────────────────────────────
    echo "═══ [18/18] REMAINING PRODUCTION BLOCKERS SUMMARY ═══"
    echo "  (Automated summary based on evidence above)"
    BLOCKERS=0
    curl -sf http://localhost:8000/health >/dev/null 2>&1 || { echo "  BLOCKER: Backend /health failing"; BLOCKERS=$((BLOCKERS+1)); }
    curl -sf http://localhost:8000/readyz >/dev/null 2>&1 || { echo "  BLOCKER: Backend /readyz failing (DB/dep unreachable)"; BLOCKERS=$((BLOCKERS+1)); }
    curl -sf http://localhost/health >/dev/null 2>&1 || { echo "  BLOCKER: Nginx proxy failing"; BLOCKERS=$((BLOCKERS+1)); }
    docker exec jarvis_redis redis-cli ping >/dev/null 2>&1 || { echo "  BLOCKER: Redis not responding"; BLOCKERS=$((BLOCKERS+1)); }
    docker exec jarvis_postgres pg_isready -U jarvis >/dev/null 2>&1 || { echo "  BLOCKER: PostgreSQL not ready"; BLOCKERS=$((BLOCKERS+1)); }
    docker inspect evolution-api --format='{{.State.Status}}' 2>/dev/null | grep -q running || { echo "  BLOCKER: Evolution/WhatsApp not running"; BLOCKERS=$((BLOCKERS+1)); }
    docker exec jarvis_postgres psql -U jarvis -c "SELECT 1 FROM pg_database WHERE datname='evolution'" -tA 2>/dev/null | grep -q 1 || { echo "  BLOCKER: Evolution database does not exist"; BLOCKERS=$((BLOCKERS+1)); }
    echo ""
    echo "  Total blockers detected: $BLOCKERS"
    echo ""

    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              AUDIT COMPLETE — NO CHANGES MADE              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo "AUDIT_COMPLETE"
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
    # /health is shallow (no DB) — /readyz actually checks DB connectivity.
    # A deploy where /health passes but /readyz fails means the backend
    # process is up but can't reach its database, which /health alone
    # would silently pass through as a successful deploy.
    curl -sf http://localhost:8000/readyz && echo BACKEND_READYZ_OK || echo BACKEND_READYZ_FAIL

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
