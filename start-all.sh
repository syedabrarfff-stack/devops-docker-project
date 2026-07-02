#!/bin/bash
# JARVIS Complete Stack Startup Script
# Starts all services: Backend, Frontend, Grafana, Loki, Prometheus, etc.

set -e

echo "🚀 JARVIS Complete Stack Startup"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Change to project root
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    exit 1
fi

# Verify critical env vars
if ! grep -q "REDIS_PASSWORD=captain" .env; then
    echo "⚠️  REDIS_PASSWORD not set in .env"
    exit 1
fi

if ! grep -q "GRAFANA_ADMIN_PASSWORD=captain" .env; then
    echo "⚠️  GRAFANA_ADMIN_PASSWORD not set in .env"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Stop existing containers (optional)
echo "📦 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to become healthy (30-60 seconds)..."
echo ""

# Function to wait for service health
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose ps | grep -q "$service.*Up.*healthy"; then
            echo "  ✅ $service is healthy"
            return 0
        fi
        echo "  ⏳ Waiting for $service... ($((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done

    echo "  ⚠️  $service is not healthy yet (may still start)"
}

# Wait for critical services
echo "Checking service health:"
wait_for_service "postgres"
wait_for_service "redis"
wait_for_service "backend"
wait_for_service "frontend"
wait_for_service "grafana"
wait_for_service "prometheus"
wait_for_service "loki"

echo ""
echo "=================================="
echo "✅ JARVIS Stack is Starting Up"
echo "=================================="
echo ""
echo "📊 Dashboard URLs:"
echo "  🖥️  Control Room:     http://localhost:3002/control-room"
echo "  📈 Grafana:          http://localhost:3001"
echo "  📋 Loki Logs:        http://localhost:3001/d/loki-logs"
echo "  📊 Prometheus:       http://localhost:9090"
echo "  🔌 Backend API:      http://localhost:8000"
echo ""
echo "🔐 Authentication:"
echo "  Username: captain"
echo "  Password: captain"
echo ""
echo "📝 Service Status:"
docker compose ps --format "table {{.Names}}\t{{.Status}}"
echo ""
echo "💡 Tips:"
echo "  • View logs:     docker compose logs -f"
echo "  • Check health:  curl http://localhost:8000/health"
echo "  • Stop all:      docker compose down"
echo "  • Restart one:   docker compose restart <service>"
echo ""
echo "🚀 Ready to use! Access http://localhost:3002/control-room"
echo ""
