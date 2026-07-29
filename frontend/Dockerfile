# Build stage
FROM node:20-alpine AS builder

# Only needed when building behind a TLS-inspecting proxy (e.g. this repo's
# dev sandbox — see /root/.ccr/ca-bundle.crt in that environment's docs).
# Real CI (GitHub Actions) and the production EC2 host have direct internet
# access and don't need this — defaulting it off keeps certificate
# verification on everywhere except when explicitly opted into.
ARG NPM_INSECURE_REGISTRY=false

WORKDIR /app
COPY package*.json ./
RUN if [ "$NPM_INSECURE_REGISTRY" = "true" ]; then npm config set strict-ssl false; fi \
    && npm ci --legacy-peer-deps
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
