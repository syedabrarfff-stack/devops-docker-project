#!/bin/bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/home/ubuntu/bunny-production/infrastructure/docker-compose.yml}"
LOG_FILE="${LOG_FILE:-/var/log/jarvis-watchdog.log}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
UNHEALTHY_THRESHOLD="${UNHEALTHY_THRESHOLD:-3}"

declare -A failure_counts

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] $1" | tee -a "$LOG_FILE"
}

restart_container() {
    local name="$1"
    log "Restarting $name"
    docker restart "$name" >>"$LOG_FILE" 2>&1 || true
    failure_counts[$name]=0
}

check_container() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")

    case "$status" in
        healthy)
            failure_counts[$name]=0
            ;;
        starting)
            log "$name is starting"
            ;;
        unhealthy|missing)
            failure_counts[$name]=$(( ${failure_counts[$name]:-0} + 1 ))
            log "$name is $status (${failure_counts[$name]}/${UNHEALTHY_THRESHOLD})"
            if [ "${failure_counts[$name]}" -ge "$UNHEALTHY_THRESHOLD" ]; then
                restart_container "$name"
            fi
            ;;
        *)
            if [ "$name" = "jarvis_nginx" ] && ! curl -sf http://localhost/health >/dev/null 2>&1; then
                failure_counts[$name]=$(( ${failure_counts[$name]:-0} + 1 ))
                log "$name HTTP health failed (${failure_counts[$name]}/${UNHEALTHY_THRESHOLD})"
                if [ "${failure_counts[$name]}" -ge "$UNHEALTHY_THRESHOLD" ]; then
                    restart_container "$name"
                fi
            else
                failure_counts[$name]=0
            fi
            ;;
    esac
}

log "JARVIS watchdog started"

while true; do
    if [ "$(docker compose -f "$COMPOSE_FILE" ps --services --filter status=running 2>/dev/null | wc -l)" -lt 3 ]; then
        log "Stack is not fully running; starting compose stack"
        docker compose -f "$COMPOSE_FILE" up -d --remove-orphans >>"$LOG_FILE" 2>&1 || true
        sleep 30
    fi

    for container in jarvis_redis jarvis_postgres jarvis_backend jarvis_frontend jarvis_nginx; do
        check_container "$container"
    done

    disk_usage=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [ "$disk_usage" -gt 90 ]; then
        log "Disk usage is ${disk_usage}%; truncating Docker JSON logs"
        truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null || true
    fi

    sleep "$CHECK_INTERVAL"
done
