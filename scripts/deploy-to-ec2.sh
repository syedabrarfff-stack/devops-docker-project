#!/bin/bash
set -e

# JARVIS EC2 Deployment Script
# Usage: ./scripts/deploy-to-ec2.sh [--server user@ip] [--key path/to/key.pem] [--full]

SERVER="${SERVER:-ubuntu@your-ec2-ip}"
KEY="${KEY:-~/.ssh/jarvis.pem}"
FULL_DEPLOY="${FULL_DEPLOY:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --server) SERVER="$2"; shift 2;;
    --key) KEY="$2"; shift 2;;
    --full) FULL_DEPLOY="true"; shift;;
    *) shift;;
  esac
done

echo "🚀 JARVIS EC2 Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Server: $SERVER"
echo "Key: $KEY"
echo "Full Deploy: $FULL_DEPLOY"
echo ""

# Step 1: Build locally
echo "📦 Building Docker images..."
docker-compose build --no-cache

# Step 2: Push code to EC2
echo "📤 Pushing code to EC2..."
rsync -avz -e "ssh -i $KEY" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'backend/venv' \
  --exclude '.env' \
  --exclude '__pycache__' \
  . $SERVER:/opt/jarvis/

# Step 3: Deploy on EC2
echo "🔧 Deploying on EC2..."
ssh -i "$KEY" "$SERVER" << 'EOF'
set -e
cd /opt/jarvis

echo "⬇️  Pulling latest code..."
git pull origin main || true

echo "🐳 Building containers..."
docker-compose build

echo "🔄 Stopping old services..."
docker-compose down || true

echo "📦 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 5

echo "🏥 Health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "✅ Backend is healthy"
else
  echo "⚠️  Backend not responding yet, retrying..."
  sleep 5
  curl http://localhost:8000/health || echo "Backend still starting"
fi

echo "📋 Service status:"
docker-compose ps

echo "🎉 Deployment complete!"
EOF

echo ""
echo "✅ Deployment successful!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Services are live:"
echo "  API: http://$SERVER/api/v1/health"
echo "  Frontend: http://$SERVER"
echo "  Logs: ssh -i $KEY $SERVER 'docker-compose logs -f'"
