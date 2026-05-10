.PHONY: up down build restart logs status \
        seed health readyz \
        psql redis-cli \
        backend frontend dev-install \
        clean prune \
        deploy-check lint

# ── Stack control ─────────────────────────────────────────────────────────────

up:
	cd infrastructure && docker compose up -d
	@echo "✅  JARVIS stack up — http://localhost"

down:
	cd infrastructure && docker compose down

build:
	cd infrastructure && docker compose build --no-cache

restart:
	cd infrastructure && docker compose restart

logs:
	cd infrastructure && docker compose logs -f

logs-backend:
	cd infrastructure && docker compose logs -f backend

logs-db:
	cd infrastructure && docker compose logs -f postgres

status:
	cd infrastructure && docker compose ps

# ── Health checks ─────────────────────────────────────────────────────────────

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not reachable"

readyz:
	@curl -s http://localhost:8000/readyz | python3 -m json.tool || echo "Backend not reachable"

# ── Data operations ───────────────────────────────────────────────────────────

seed:
	@echo "Seeding service catalog…"
	@curl -s -X POST http://localhost:8000/api/v1/catalog/seed | python3 -m json.tool
	@echo "Seeding team registry…"
	@curl -s -X POST http://localhost:8000/api/v1/team/seed | python3 -m json.tool

# ── Database shell ────────────────────────────────────────────────────────────

psql:
	cd infrastructure && docker compose exec postgres psql -U jarvis -d jarvis

redis-cli:
	cd infrastructure && docker compose exec redis redis-cli

# ── Local development (no Docker) ─────────────────────────────────────────────

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev-install:
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

# ── Pre-deploy validation ─────────────────────────────────────────────────────

deploy-check:
	@bash scripts/pre-deploy-check.sh

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	cd infrastructure && docker compose down -v
	@echo "⚠️  Volumes removed — data cleared"

prune:
	docker system prune -f
	docker volume prune -f

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	cd backend && python3 -m py_compile app/main.py && echo "✅ main.py OK"
	cd frontend && npm run lint --if-present || true
