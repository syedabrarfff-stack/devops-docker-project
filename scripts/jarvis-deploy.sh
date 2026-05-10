#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — Aliyar Solutions
# One-Command Full Production Deployment Script
#
# Usage: bash jarvis-deploy.sh
# Run this once on your EC2 Ubuntu server — it handles everything.
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
log()     { echo -e "${CYAN}[JARVIS]${NC} $1"; }
success() { echo -e "${GREEN}[✅ DONE]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠️  WARN]${NC} $1"; }
error()   { echo -e "${RED}[❌ ERROR]${NC} $1"; exit 1; }
header()  { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${WHITE}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}\n"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║     JARVIS — Aliyar Solutions             ║"
echo "  ║     Full Production Deployment            ║"
echo "  ║     One script. Everything automated.     ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ── Collect configuration ─────────────────────────────────────────────────────
header "STEP 1 — Configuration"

echo -e "${WHITE}Enter your configuration (press Enter to skip optional items):${NC}\n"

read -p "GitHub repo URL (e.g. https://github.com/user/devops-docker-project): " REPO_URL
read -p "Your domain name (e.g. aliyarsolutions.com) or press Enter to skip SSL: " DOMAIN
read -p "Your email (for SSL certificate): " SSL_EMAIL
echo ""
echo -e "${WHITE}API Keys (paste each one):${NC}"
read -p "Anthropic API Key (sk-ant-...): " ANTHROPIC_KEY
read -p "OpenAI API Key (sk-...): " OPENAI_KEY
read -p "Stripe Secret Key (sk_live_... or sk_test_...): " STRIPE_KEY
read -p "Slack Webhook URL (https://hooks.slack.com/...): " SLACK_WEBHOOK
echo ""
read -p "PostgreSQL password (choose a strong password): " DB_PASSWORD
read -p "Secret key for JWT (random string, min 32 chars): " SECRET_KEY
echo ""

# Defaults
REPO_URL=${REPO_URL:-"https://github.com/syedabrarfff-stack/devops-docker-project.git"}
DB_PASSWORD=${DB_PASSWORD:-"jarvis_secure_$(date +%s)"}
SECRET_KEY=${SECRET_KEY:-"jarvis_secret_$(openssl rand -hex 16 2>/dev/null || echo 'default_secret_key_change_me')"}
DEPLOY_DIR="/home/ubuntu/devops-docker-project"
APP_URL="http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'localhost')"
[ -n "$DOMAIN" ] && APP_URL="https://$DOMAIN"

echo ""
log "Configuration collected. Starting deployment..."
sleep 2

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 2 — System Update & Dependencies"
# ═══════════════════════════════════════════════════════════════════════════════

log "Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq
sudo apt-get install -y -qq \
    git curl wget nano htop \
    ca-certificates gnupg lsb-release \
    python3 python3-pip \
    nginx certbot python3-certbot-nginx \
    ufw fail2ban
success "System packages installed"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 3 — Install Docker"
# ═══════════════════════════════════════════════════════════════════════════════

if command -v docker &>/dev/null; then
    success "Docker already installed: $(docker --version)"
else
    log "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh -q
    sudo usermod -aG docker ubuntu
    sudo systemctl enable docker
    sudo systemctl start docker
    rm /tmp/get-docker.sh
    success "Docker installed"
fi

if docker compose version &>/dev/null 2>&1; then
    success "Docker Compose already available"
else
    log "Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin -qq
    success "Docker Compose installed"
fi

# Apply docker group without logout
if ! groups ubuntu | grep -q docker; then
    sudo usermod -aG docker ubuntu
fi

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 4 — Clone JARVIS Repository"
# ═══════════════════════════════════════════════════════════════════════════════

if [ -d "$DEPLOY_DIR" ]; then
    log "Repository exists. Pulling latest changes..."
    cd "$DEPLOY_DIR"
    git pull origin main 2>/dev/null || git pull origin claude/jarvis-cans-api-integration-ZThTD 2>/dev/null || warn "Git pull failed — continuing with existing code"
else
    log "Cloning JARVIS repository..."
    git clone "$REPO_URL" "$DEPLOY_DIR"
    success "Repository cloned to $DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 5 — Create Environment Configuration"
# ═══════════════════════════════════════════════════════════════════════════════

log "Writing .env file..."
cat > "$DEPLOY_DIR/.env" << EOF
# ─── JARVIS Production Environment ───────────────────────────────────────────
# Generated by jarvis-deploy.sh on $(date)

# Application
ENVIRONMENT=production
DEBUG=false
APP_VERSION=9.0.0
APP_BASE_URL=$APP_URL
SECRET_KEY=$SECRET_KEY

# Database
POSTGRES_DB=jarvis
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://jarvis:${DB_PASSWORD}@postgres:5432/jarvis

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:80,$APP_URL

# AI Providers
ANTHROPIC_API_KEY=${ANTHROPIC_KEY:-""}
OPENAI_API_KEY=${OPENAI_KEY:-""}
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
GROQ_API_KEY=
MISTRAL_API_KEY=

# Payments
STRIPE_SECRET_KEY=${STRIPE_KEY:-""}
STRIPE_WEBHOOK_SECRET=

# Notifications
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK:-""}

# Email (optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EOF

chmod 600 "$DEPLOY_DIR/.env"
success ".env file created and secured"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 6 — Configure Nginx"
# ═══════════════════════════════════════════════════════════════════════════════

log "Writing Nginx configuration..."

sudo mkdir -p /etc/nginx/conf.d

if [ -n "$DOMAIN" ]; then
    SERVER_NAME="$DOMAIN www.$DOMAIN"
else
    SERVER_NAME="_"
fi

sudo tee /etc/nginx/conf.d/jarvis.conf > /dev/null << EOF
# JARVIS — Aliyar Solutions
# Nginx reverse proxy configuration

upstream jarvis_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream jarvis_frontend {
    server 127.0.0.1:3000;
    keepalive 16;
}

server {
    listen 80;
    server_name $SERVER_NAME;
    client_max_body_size 50M;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1000;

    # API routes → Backend
    location /api/ {
        proxy_pass http://jarvis_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }

    # Health endpoints → Backend
    location ~ ^/(health|readyz|docs) {
        proxy_pass http://jarvis_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Frontend → React app
    location / {
        proxy_pass http://jarvis_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Remove default nginx config
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Test and reload nginx
sudo nginx -t && sudo systemctl reload nginx
success "Nginx configured"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 7 — Configure Firewall"
# ═══════════════════════════════════════════════════════════════════════════════

log "Setting up UFW firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
success "Firewall configured — SSH + HTTP + HTTPS allowed"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 8 — Start JARVIS Services"
# ═══════════════════════════════════════════════════════════════════════════════

cd "$DEPLOY_DIR/infrastructure"

log "Pulling Docker images..."
sudo docker compose pull 2>/dev/null || docker compose pull 2>/dev/null || true

log "Starting all JARVIS services..."
sudo docker compose up -d --build 2>/dev/null || docker compose up -d --build

log "Waiting for services to initialize (30 seconds)..."
sleep 30

log "Checking service health..."
sudo docker compose ps 2>/dev/null || docker compose ps

success "JARVIS services started"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 9 — SSL Certificate (HTTPS)"
# ═══════════════════════════════════════════════════════════════════════════════

if [ -n "$DOMAIN" ] && [ -n "$SSL_EMAIL" ]; then
    log "Setting up SSL certificate for $DOMAIN..."
    sudo certbot --nginx \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email "$SSL_EMAIL" \
        --agree-tos \
        --non-interactive \
        --redirect 2>/dev/null && success "SSL certificate installed — HTTPS active" \
        || warn "SSL setup failed — you can run: sudo certbot --nginx -d $DOMAIN manually"

    # Auto-renewal cron
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
    success "SSL auto-renewal configured"
else
    warn "No domain provided — skipping SSL. Add domain later with: sudo certbot --nginx -d yourdomain.com"
fi

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 10 — Auto-Restart on Reboot"
# ═══════════════════════════════════════════════════════════════════════════════

log "Creating systemd service for auto-restart..."
sudo tee /etc/systemd/system/jarvis.service > /dev/null << EOF
[Unit]
Description=JARVIS — Aliyar Solutions
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR/infrastructure
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jarvis.service
success "JARVIS will auto-start on every server reboot"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 11 — Health Monitoring Cron"
# ═══════════════════════════════════════════════════════════════════════════════

log "Setting up health check cron job..."
(crontab -l 2>/dev/null; echo "*/5 * * * * curl -sf http://localhost:8000/health > /dev/null || echo 'JARVIS health check failed' | logger -t jarvis") | crontab -
success "Health monitoring active (every 5 minutes)"

# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 12 — Final Health Verification"
# ═══════════════════════════════════════════════════════════════════════════════

log "Running health checks..."
sleep 5

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HEALTH" = "200" ]; then
    success "Backend health check: HTTP 200 ✅"
else
    warn "Backend health check: HTTP $HEALTH — may still be starting up"
fi

NGINX_STATUS=$(sudo systemctl is-active nginx 2>/dev/null || echo "unknown")
if [ "$NGINX_STATUS" = "active" ]; then
    success "Nginx: active ✅"
else
    warn "Nginx status: $NGINX_STATUS"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT COMPLETE
# ═══════════════════════════════════════════════════════════════════════════════

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
echo -e "${GREEN}"
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║                                                           ║"
echo "  ║   ✅  JARVIS IS LIVE — ALIYAR SOLUTIONS                  ║"
echo "  ║                                                           ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${WHITE}Access JARVIS:${NC}"
if [ -n "$DOMAIN" ]; then
echo -e "  🌐 Website:   ${CYAN}https://$DOMAIN${NC}"
echo -e "  ⚡ API:       ${CYAN}https://$DOMAIN/health${NC}"
echo -e "  📊 Readyz:    ${CYAN}https://$DOMAIN/readyz${NC}"
echo -e "  📚 API Docs:  ${CYAN}https://$DOMAIN/docs${NC}"
else
echo -e "  🌐 Website:   ${CYAN}http://$PUBLIC_IP${NC}"
echo -e "  ⚡ API:       ${CYAN}http://$PUBLIC_IP/health${NC}"
echo -e "  📊 Readyz:    ${CYAN}http://$PUBLIC_IP/readyz${NC}"
echo -e "  📚 API Docs:  ${CYAN}http://$PUBLIC_IP/docs${NC}"
fi
echo ""
echo -e "${WHITE}Useful commands:${NC}"
echo -e "  ${CYAN}cd $DEPLOY_DIR/infrastructure && docker compose ps${NC}     — check services"
echo -e "  ${CYAN}docker compose logs -f backend${NC}                          — live logs"
echo -e "  ${CYAN}docker compose restart backend${NC}                          — restart backend"
echo -e "  ${CYAN}make health${NC}                                              — quick health check"
echo -e "  ${CYAN}make logs${NC}                                                — all logs"
echo ""
echo -e "${WHITE}Next steps:${NC}"
echo -e "  1. Visit your URL above and verify JARVIS loads"
echo -e "  2. Set up GitHub Actions for auto-deploy (see deployment guide)"
echo -e "  3. Configure your domain DNS if not done"
echo -e "  4. Start outreach to first clients"
echo ""
echo -e "${BLUE}Aliyar Solutions — Operational. Professional. Global.${NC}"
echo ""
