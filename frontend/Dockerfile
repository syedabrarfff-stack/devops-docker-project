# Build stage
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm config set strict-ssl false && npm ci --legacy-peer-deps
COPY . .
RUN npm run build

# Serve stage
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
# Template-based config: BACKEND_HOST selects upstream at runtime
# Local Compose: BACKEND_HOST=backend | ECS sidecar: BACKEND_HOST=localhost
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["/docker-entrypoint.sh"]
