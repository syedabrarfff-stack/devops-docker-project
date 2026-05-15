#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS Watchdog — keeps all containers alive 24/7
# Install as a systemd service or run in a screen/tmux session.
#
# Usage:
#   chmod +x scripts/watchdog.sh
#   bash scripts/watchdog.sh
#
# As systemd service — add to /etc/systemd/system/jarvis-watchdog.service
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

COMPOSE_FILE="/home/ubuntu/devops-docker-project/infrastructure/docker-compose.yml"
LOG_FILE="/var/log/jarvis-watchdog.log"
CHECK_INTERVAL=30        # seconds between health checks
UNHEALTHY_THRESHOLD=3    # restarts after N consecutive failures
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()   { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] $1" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}$(date '+%H:%M:%S') ✓ $1${NC}"; }
warn()  { echo -e "${YELLOW}$(date '+%H:%M:%S') ⚠ $1${NC}"; }
error() { echo -e "${RED}$(date '+%H:%M:%S') ✗ $1${NC}"; }

declare -A failure_counts

notify_slack() {
    local msg="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            --data "{\"text\":\"🔴 JARVIS Watchdog: $msg\"}" >/dev/null 2>&1 || true
    fi
}

check_container() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")

    case "$status" in
        "healthy")
            failure_counts[$name]=0
            ok "$name is healthy"
            ;;
        "starting")
            warn "$name is starting up..."
            ;;
        "unhealthy"|"missing")
            failure_counts[$name]=$(( ${failure_counts[$name]:-0} + 1 ))
            local count=${failure_counts[$name]}
            error "$name is $status (failure #$count)"

            if [ "$count" -ge "$UNHEALTHY_THRESHOLD" ]; then
                log "RESTARTING $name after $count consecutive failures"
                notify_slack "$name was $status — restarting now"
                docker restart "$name" 2>&1 | tee -a "$LOG_FILE" || true
                failure_counts[$name]=0
                sleep 10
            fi
            ;;
        *)
            warn "$name has no healthcheck (status: $status)"
            # For nginx which has no Docker healthcheck, check HTTP
            if [ "$name" = "jarvis_nginx" ]; then
                if ! curl -sf http://localhost/health >/dev/null 2>&1; then
                    failure_counts[$name]=$(( ${failure_counts[$name]:-0} + 1 ))
                    local count=${failure_counts[$name]}
                    error "nginx HTTP health failed (failure #$count)"
                    if [ "$count" -ge "$UNHEALTHY_THRESHOLD" ]; then
                        log "RESTARTING jarvis_nginx"
                        docker restart jarvis_nginx 2>&1 | tee -a "$LOG_FILE" || true
                        failure_counts[$name]=0
                    fi
                else
                    failure_counts[$name]=0
                    ok "nginx is reachable (HTTP)"
                fi
            fi
            ;;
    esac
}

ensure_stack_running() {
    local running
    running=$(docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running" 2>/dev/null | wc -l)
    if [ "$running" -lt 3 ]; then
        log "Stack not fully running ($running containers). Starting up..."
        docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1 | tee -a "$LOG_FILE"
        sleep 30
    fi
}

log "JARVIS Watchdog starting — checking every ${CHECK_INTERVAL}s"

while true; do
    echo -e "\n$(date '+%Y-%m-%d %H:%M:%S') ─────────────────────────────────"

    ensure_stack_running

    for container in jarvis_redis jarvis_postgres jarvis_backend jarvis_frontend jarvis_nginx; do
        check_container "$container"
    done

    # Disk space guard — restart backend if >90% disk used (logs can fill it)
    disk_usage=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [ "$disk_usage" -gt 90 ]; then
        warn "Disk usage at ${disk_usage}% — clearing Docker logs"
        truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null || true
        notify_slack "Disk at ${disk_usage}% on JARVIS server. Docker logs cleared."
    fi

    sleep "$CHECK_INTERVAL"
done
