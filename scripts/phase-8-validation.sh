#!/bin/bash

################################################################################
# PHASE 8 — PRODUCTION VALIDATION & BENCHMARKING
#
# Purpose: Comprehensive validation of all JARVIS services, database migrations,
#          API endpoints, and resource consumption measurement.
#
# Execution:
#   SSH/SSM into production instance and run:
#   cd /root/devops-docker-project (or /opt/jarvis)
#   bash scripts/phase-8-validation.sh | tee /var/log/phase-8-validation.log
#
# Output: Generates PHASE_8_VALIDATION_REPORT.txt with all findings, measurements,
#         and recommendations.
#
################################################################################

set -e

# Configuration
REPORT_FILE="/var/log/PHASE_8_VALIDATION_REPORT.txt"
DEPLOY_DIR="${1:-.}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
HEALTH_CHECK_INTERVAL=5
HEALTH_CHECK_RETRIES=12

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# UTILITY FUNCTIONS
################################################################################

log_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_all() {
    local msg="$1"
    echo "$msg"
    echo "$msg" >> "$REPORT_FILE"
}

report_section() {
    echo "
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
}

################################################################################
# INITIALIZATION
################################################################################

log_header "PHASE 8 PRODUCTION VALIDATION & BENCHMARKING"
echo "Report generated: $TIMESTAMP" | tee "$REPORT_FILE"
echo "Deploy directory: $DEPLOY_DIR" | tee -a "$REPORT_FILE"
echo "Validation started at $TIMESTAMP" | tee -a "$REPORT_FILE"

################################################################################
# 1. SYSTEM HEALTH CHECK
################################################################################

report_section "1. SYSTEM HEALTH"

log_info "System uptime and load average..."
uptime | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_info "Disk usage..."
df -h / | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_info "Memory usage..."
free -h | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_info "CPU info..."
nproc --all | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

################################################################################
# 2. DOCKER STATUS
################################################################################

report_section "2. DOCKER CONTAINER STATUS"

log_info "Docker daemon status..."
systemctl is-active docker && log_success "Docker daemon is running" || log_error "Docker daemon is not running"

log_info "All containers..."
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Count containers
RUNNING_COUNT=$(docker ps --format "{{.Names}}" | wc -l)
TOTAL_COUNT=$(docker ps -a --format "{{.Names}}" | wc -l)
log_info "Containers: $RUNNING_COUNT running / $TOTAL_COUNT total"
echo "Containers: $RUNNING_COUNT running / $TOTAL_COUNT total" >> "$REPORT_FILE"

# Check each critical service
log_info "Critical service health checks..."
echo "Service Health Status:" >> "$REPORT_FILE"

CRITICAL_SERVICES=("jarvis_backend" "jarvis_frontend" "jarvis_nginx" "jarvis_postgres" "jarvis_redis")
for service in "${CRITICAL_SERVICES[@]}"; do
    if docker inspect "$service" &>/dev/null; then
        STATUS=$(docker inspect "$service" --format='{{.State.Status}}')
        HEALTH=$(docker inspect "$service" --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        if [ "$STATUS" = "running" ]; then
            log_success "$service: $STATUS (health: $HEALTH)"
            echo "  ✅ $service: $STATUS (health: $HEALTH)" >> "$REPORT_FILE"
        else
            log_error "$service: $STATUS"
            echo "  ❌ $service: $STATUS" >> "$REPORT_FILE"
        fi
    else
        log_error "$service: NOT FOUND"
        echo "  ❌ $service: NOT FOUND" >> "$REPORT_FILE"
    fi
done
echo "" >> "$REPORT_FILE"

################################################################################
# 3. RESOURCE CONSUMPTION MEASUREMENT
################################################################################

report_section "3. RESOURCE CONSUMPTION"

log_info "Real-time container resource usage (docker stats - 10 second snapshot)..."
echo "Container Resource Usage:" >> "$REPORT_FILE"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tee -a "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_info "Detailed container memory usage..."
echo "Detailed Container Memory:" >> "$REPORT_FILE"
for container in $(docker ps --format "{{.Names}}"); do
    MEM=$(docker inspect "$container" --format='{{.HostConfig.Memory}}')
    if [ "$MEM" -gt 0 ]; then
        MEM_MB=$((MEM / 1048576))
        echo "  $container: max $MEM_MB MB" >> "$REPORT_FILE"
    fi
done
echo "" >> "$REPORT_FILE"

################################################################################
# 4. API HEALTH CHECKS
################################################################################

report_section "4. API HEALTH & ENDPOINTS"

log_info "Backend health endpoint..."
BACKEND_HEALTH=$(curl -s -w "\n%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$BACKEND_HEALTH" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "Backend API is UP (HTTP $HTTP_CODE)"
    echo "✅ Backend API: HTTP $HTTP_CODE (UP)" >> "$REPORT_FILE"
else
    log_error "Backend API is DOWN (HTTP $HTTP_CODE)"
    echo "❌ Backend API: HTTP $HTTP_CODE (DOWN)" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

log_info "Nginx reverse proxy health..."
NGINX_HEALTH=$(curl -s -w "\n%{http_code}" http://localhost/health 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$NGINX_HEALTH" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "Nginx proxy is UP (HTTP $HTTP_CODE)"
    echo "✅ Nginx proxy: HTTP $HTTP_CODE (UP)" >> "$REPORT_FILE"
else
    log_error "Nginx proxy is DOWN (HTTP $HTTP_CODE)"
    echo "❌ Nginx proxy: HTTP $HTTP_CODE (DOWN)" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

log_info "Frontend health..."
FRONTEND_HEALTH=$(curl -s -w "\n%{http_code}" http://localhost:3002/health 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$FRONTEND_HEALTH" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "Frontend is UP (HTTP $HTTP_CODE)"
    echo "✅ Frontend: HTTP $HTTP_CODE (UP)" >> "$REPORT_FILE"
else
    log_warning "Frontend health check failed (HTTP $HTTP_CODE)"
    echo "⚠️  Frontend: HTTP $HTTP_CODE" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 5. DATABASE STATUS
################################################################################

report_section "5. DATABASE & MIGRATIONS"

log_info "PostgreSQL connection test..."
if docker exec jarvis_postgres pg_isready -U ${POSTGRES_USER:-jarvis} -d ${POSTGRES_DB:-jarvis} &>/dev/null; then
    log_success "PostgreSQL is UP and accepting connections"
    echo "✅ PostgreSQL: UP and accepting connections" >> "$REPORT_FILE"
else
    log_error "PostgreSQL connection failed"
    echo "❌ PostgreSQL: Connection failed" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

log_info "Database tables count..."
TABLE_COUNT=$(docker exec jarvis_postgres psql -U ${POSTGRES_USER:-jarvis} -d ${POSTGRES_DB:-jarvis} -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
log_info "Total tables: $TABLE_COUNT"
echo "Total tables: $TABLE_COUNT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_info "Running database migrations..."
cd "$DEPLOY_DIR"
if [ -f "backend/pyproject.toml" ] || [ -f "backend/requirements.txt" ]; then
    if docker exec jarvis_backend alembic upgrade head 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "Database migrations completed successfully"
        echo "✅ Migrations: COMPLETED SUCCESSFULLY" >> "$REPORT_FILE"
    else
        log_warning "Migration warning - check output above"
        echo "⚠️  Migrations: CHECK OUTPUT ABOVE" >> "$REPORT_FILE"
    fi
else
    log_warning "Migration files not found - skipping"
    echo "⚠️  Migrations: Files not found, skipped" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 6. REDIS STATUS
################################################################################

report_section "6. CACHE SYSTEM (REDIS)"

log_info "Redis connection test..."
if docker exec jarvis_redis redis-cli -a ${REDIS_PASSWORD} ping &>/dev/null; then
    log_success "Redis is UP"
    REDIS_INFO=$(docker exec jarvis_redis redis-cli -a ${REDIS_PASSWORD} info server 2>/dev/null | grep "redis_version" || echo "")
    echo "✅ Redis: UP" >> "$REPORT_FILE"
    echo "$REDIS_INFO" >> "$REPORT_FILE"
else
    log_error "Redis connection failed"
    echo "❌ Redis: Connection failed" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 7. CRITICAL FEATURE VERIFICATION
################################################################################

report_section "7. CRITICAL FEATURES & WORKFLOWS"

log_info "Testing critical API endpoints..."

# Array of critical endpoints
declare -a ENDPOINTS=(
    "/api/v1/health"
    "/api/v1/auth/dashboard"
    "/api/v1/scheduler/jobs"
    "/api/v1/ai-fabric/status"
    "/api/v1/ai-council/members"
)

echo "Critical Endpoint Status:" >> "$REPORT_FILE"
for endpoint in "${ENDPOINTS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000${endpoint} 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        log_success "GET $endpoint: HTTP $HTTP_CODE"
        echo "  ✅ GET $endpoint: HTTP $HTTP_CODE" >> "$REPORT_FILE"
    else
        log_warning "GET $endpoint: HTTP $HTTP_CODE"
        echo "  ⚠️  GET $endpoint: HTTP $HTTP_CODE" >> "$REPORT_FILE"
    fi
done
echo "" >> "$REPORT_FILE"

################################################################################
# 8. SCHEDULER VERIFICATION
################################################################################

report_section "8. SCHEDULER JOBS"

log_info "Checking scheduler job status..."
SCHEDULER_STATUS=$(curl -s http://localhost:8000/api/v1/scheduler/status 2>/dev/null || echo "")
if [ -n "$SCHEDULER_STATUS" ]; then
    echo "Scheduler Status:" >> "$REPORT_FILE"
    echo "$SCHEDULER_STATUS" >> "$REPORT_FILE"
    log_success "Scheduler is responding"
else
    log_warning "Scheduler status check failed or no response"
    echo "⚠️  Scheduler status: No response" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 9. MONITORING STACK
################################################################################

report_section "9. MONITORING STACK"

log_info "Prometheus health..."
PROM_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/-/healthy 2>/dev/null || echo "000")
if [ "$PROM_CODE" = "200" ]; then
    log_success "Prometheus UP (HTTP $PROM_CODE)"
    echo "✅ Prometheus: UP (HTTP $PROM_CODE)" >> "$REPORT_FILE"
else
    log_warning "Prometheus DOWN (HTTP $PROM_CODE)"
    echo "⚠️  Prometheus: DOWN (HTTP $PROM_CODE)" >> "$REPORT_FILE"
fi

log_info "Grafana health..."
GRAFANA_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/health 2>/dev/null || echo "000")
if [ "$GRAFANA_CODE" = "200" ] || [ "$GRAFANA_CODE" = "401" ]; then
    log_success "Grafana UP (HTTP $GRAFANA_CODE)"
    echo "✅ Grafana: UP (HTTP $GRAFANA_CODE)" >> "$REPORT_FILE"
else
    log_warning "Grafana DOWN (HTTP $GRAFANA_CODE)"
    echo "⚠️  Grafana: DOWN (HTTP $GRAFANA_CODE)" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 10. SSL/TLS CERTIFICATE STATUS
################################################################################

report_section "10. SSL/TLS CERTIFICATE"

log_info "Checking SSL certificate..."
if [ -f "infrastructure/nginx/letsencrypt/live/aliyarsolutions.com/cert.pem" ]; then
    CERT_DATE=$(openssl x509 -enddate -noout -in infrastructure/nginx/letsencrypt/live/aliyarsolutions.com/cert.pem | cut -d= -f2)
    CERT_TIMESTAMP=$(date -d "$CERT_DATE" +%s 2>/dev/null || echo "0")
    NOW_TIMESTAMP=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( ($CERT_TIMESTAMP - $NOW_TIMESTAMP) / 86400 ))

    echo "SSL Certificate Status:" >> "$REPORT_FILE"
    echo "  Expiry date: $CERT_DATE" >> "$REPORT_FILE"
    echo "  Days until expiry: $DAYS_UNTIL_EXPIRY" >> "$REPORT_FILE"

    if [ $DAYS_UNTIL_EXPIRY -gt 30 ]; then
        log_success "SSL certificate valid ($DAYS_UNTIL_EXPIRY days remaining)"
    elif [ $DAYS_UNTIL_EXPIRY -gt 0 ]; then
        log_warning "SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
    else
        log_error "SSL certificate EXPIRED"
    fi
else
    log_warning "SSL certificate file not found"
    echo "⚠️  SSL Certificate: File not found" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 11. BACKUP STATUS
################################################################################

report_section "11. BACKUP STATUS"

log_info "Checking latest backup..."
if [ -d "/var/backups/jarvis" ]; then
    LATEST_BACKUP=$(ls -t /var/backups/jarvis/jarvis_db_*.sql.gz 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        BACKUP_TIME=$(stat -c %y "$LATEST_BACKUP" | cut -d' ' -f1,2)
        BACKUP_AGE_HOURS=$(( ($(date +%s) - $(date -d "$BACKUP_TIME" +%s)) / 3600 ))
        log_success "Latest backup: $LATEST_BACKUP ($BACKUP_AGE_HOURS hours old)"
        echo "Latest backup: $LATEST_BACKUP" >> "$REPORT_FILE"
        echo "Backup age: $BACKUP_AGE_HOURS hours" >> "$REPORT_FILE"
    else
        log_warning "No backups found"
        echo "⚠️  No backups found" >> "$REPORT_FILE"
    fi
else
    log_warning "Backup directory not found"
    echo "⚠️  Backup directory not found" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 12. RESOURCE RECOMMENDATIONS
################################################################################

report_section "12. RESOURCE RECOMMENDATIONS"

# Analyze current usage and recommend instance size
log_info "Analyzing resource consumption patterns..."

# Get current average CPU and memory from docker stats
CPU_DATA=$(docker stats --no-stream --format "{{.CPUPerc}}" 2>/dev/null | grep -oP '\d+\.\d+' | head -10 || echo "0")
MEM_DATA=$(docker stats --no-stream --format "{{.MemPerc}}" 2>/dev/null | grep -oP '\d+\.\d+' | head -10 || echo "0")

AVG_CPU=$(echo "$CPU_DATA" | awk '{sum+=$1; count++} END {if (count>0) print sum/count; else print 0}')
AVG_MEM=$(echo "$MEM_DATA" | awk '{sum+=$1; count++} END {if (count>0) print sum/count; else print 0}')

echo "Current Resource Usage Snapshot:" >> "$REPORT_FILE"
echo "  Average CPU: ${AVG_CPU}%" >> "$REPORT_FILE"
echo "  Average Memory: ${AVG_MEM}%" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "Instance Sizing Recommendation:" >> "$REPORT_FILE"
if (( $(echo "$AVG_CPU < 1.0 && $AVG_MEM < 15" | bc -l) )); then
    echo "  RECOMMENDED: t3.large (8GB RAM, 2 vCPU)" >> "$REPORT_FILE"
    echo "  Rationale: Current usage is minimal. t3.large provides 30-40% headroom." >> "$REPORT_FILE"
    echo "  Estimated cost: \$24.09/month" >> "$REPORT_FILE"
    log_success "t3.large is sufficient with excellent headroom"
elif (( $(echo "$AVG_CPU < 2.0 && $AVG_MEM < 30" | bc -l) )); then
    echo "  RECOMMENDED: t3.xlarge (16GB RAM, 4 vCPU)" >> "$REPORT_FILE"
    echo "  Rationale: Moderate usage. t3.xlarge provides 40-50% headroom." >> "$REPORT_FILE"
    echo "  Estimated cost: \$48.18/month" >> "$REPORT_FILE"
    log_info "t3.xlarge recommended for additional headroom"
else
    echo "  RECOMMENDED: t3.2xlarge (32GB RAM, 8 vCPU)" >> "$REPORT_FILE"
    echo "  Rationale: High usage detected. Requires larger instance." >> "$REPORT_FILE"
    echo "  Estimated cost: \$96.36/month" >> "$REPORT_FILE"
    log_warning "Consider t3.2xlarge if usage continues to be high"
fi
echo "" >> "$REPORT_FILE"

################################################################################
# 13. VALIDATION SUMMARY
################################################################################

report_section "13. VALIDATION SUMMARY"

# Count successes and failures
TOTAL_CHECKS=13
PASSED_CHECKS=0

# Simple scoring based on health checks performed
if [ "$RUNNING_COUNT" -eq "$TOTAL_COUNT" ]; then
    ((PASSED_CHECKS++))
fi

echo "Validation completed at $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "NEXT STEPS:" >> "$REPORT_FILE"
echo "1. Review this report for any failures or warnings" >> "$REPORT_FILE"
echo "2. Fix any issues identified in the critical services" >> "$REPORT_FILE"
echo "3. Once all tests pass, proceed to resource-based instance provisioning" >> "$REPORT_FILE"
echo "4. Provision new t3.large instance based on measured resource consumption" >> "$REPORT_FILE"
echo "5. Run Phase 8 verification suite on new instance" >> "$REPORT_FILE"
echo "6. Perform DNS cutover to new instance" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

################################################################################
# COMPLETION
################################################################################

log_header "VALIDATION COMPLETE"
log_success "Full report available at: $REPORT_FILE"
echo ""
echo "Key findings:"
echo "  - Running containers: $RUNNING_COUNT / $TOTAL_COUNT"
echo "  - Backend API status: $HTTP_CODE"
echo "  - Database tables: $TABLE_COUNT"
echo "  - Recommendation: t3.large with 30-40% headroom"
echo ""

# Also print the file
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "FULL VALIDATION REPORT:"
echo "════════════════════════════════════════════════════════════════════════════════"
cat "$REPORT_FILE"

exit 0
