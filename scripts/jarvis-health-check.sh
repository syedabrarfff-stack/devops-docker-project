#!/bin/bash
# JARVIS Phase 1 Health Check & Auto-Healing Script
# Monitors container health, disk space, memory, SSL certificates
# Performs automatic recovery actions when issues detected

set -euo pipefail

LOG_FILE="/var/log/jarvis-health-check.log"
ALERT_THRESHOLD_DISK_PERCENT=85
ALERT_THRESHOLD_MEMORY_PERCENT=85
SSL_EXPIRY_WARNING_DAYS=30
DOCKER_COMPOSE_DIR="/root/devops-docker-project/infrastructure"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Alert function (logs critical issues)
alert() {
    log "⚠️  ALERT: $*"
    # TODO: Send to CloudWatch / SNS / Telegram in production
}

# Health check function
check_container_health() {
    local container=$1
    local status=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")

    case "$status" in
        "healthy")
            log "✓ $container: healthy"
            return 0
            ;;
        "unhealthy")
            log "✗ $container: UNHEALTHY - attempting restart"
            docker restart "$container"
            log "✓ $container: restarted"
            return 1
            ;;
        "starting")
            log "⟳ $container: starting"
            return 0
            ;;
        *)
            log "? $container: unknown status ($status)"
            return 1
            ;;
    esac
}

# Disk space check
check_disk_space() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    if (( usage > ALERT_THRESHOLD_DISK_PERCENT )); then
        alert "Disk usage: ${usage}% (threshold: ${ALERT_THRESHOLD_DISK_PERCENT}%)"

        # Attempt cleanup
        log "Attempting docker system prune..."
        docker system prune -f --volumes || true

        usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
        log "Disk usage after cleanup: ${usage}%"
    else
        log "✓ Disk usage: ${usage}%"
    fi
}

# Memory check
check_memory() {
    local usage=$(free | awk '/^Mem/ {printf("%d", $3/$2 * 100)}')

    if (( usage > ALERT_THRESHOLD_MEMORY_PERCENT )); then
        alert "Memory usage: ${usage}% (threshold: ${ALERT_THRESHOLD_MEMORY_PERCENT}%)"
    else
        log "✓ Memory usage: ${usage}%"
    fi
}

# SSL certificate expiry check
check_ssl_expiry() {
    local cert_path="/root/devops-docker-project/infrastructure/nginx/letsencrypt/live/aliyarsolutions.com/fullchain.pem"

    if [ ! -f "$cert_path" ]; then
        log "⚠ SSL certificate not found at $cert_path"
        return 1
    fi

    local expiry_date=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry_date" +%s)
    local current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

    if (( days_until_expiry <= 0 )); then
        alert "SSL certificate EXPIRED"
        log "Certificate expired on: $expiry_date"
    elif (( days_until_expiry <= SSL_EXPIRY_WARNING_DAYS )); then
        alert "SSL certificate expires in $days_until_expiry days (warning threshold: $SSL_EXPIRY_WARNING_DAYS)"
    else
        log "✓ SSL certificate valid for $days_until_expiry more days"
    fi
}

# Backup status check
check_backup_status() {
    local backup_log="/var/backups/jarvis/backups.log"

    if [ ! -f "$backup_log" ]; then
        alert "No backup log found"
        return 1
    fi

    local last_backup_line=$(tail -1 "$backup_log")
    local last_backup_time=$(echo "$last_backup_line" | awk '{print $1}')
    local last_backup_epoch=$(date -d "$last_backup_time" +%s)
    local current_epoch=$(date +%s)
    local hours_since_backup=$(( (current_epoch - last_backup_epoch) / 3600 ))

    if (( hours_since_backup > 26 )); then
        alert "Last backup was $hours_since_backup hours ago (expected daily)"
    else
        log "✓ Last backup: $hours_since_backup hours ago"
    fi
}

# Docker Compose daemon check
check_docker_daemon() {
    if docker ps >/dev/null 2>&1; then
        log "✓ Docker daemon: running"
    else
        alert "Docker daemon: NOT RUNNING"
        systemctl restart docker
        log "Docker daemon restarted"
    fi
}

# Main health check routine
main() {
    log "=== JARVIS Health Check Started ==="

    check_docker_daemon
    check_container_health "jarvis_postgres"
    check_container_health "jarvis_redis"
    check_container_health "jarvis_backend"
    check_container_health "jarvis_frontend"
    check_container_health "jarvis_nginx"
    check_disk_space
    check_memory
    check_ssl_expiry
    check_backup_status

    log "=== JARVIS Health Check Completed ==="
}

main "$@"
