.PHONY: help dev test lint deploy deploy-ec2 logs restart

help:
	@echo "JARVIS Development Commands"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Local Development:"
	@echo "  make dev              - Start backend + frontend locally"
	@echo "  make backend          - Start just backend API"
	@echo "  make frontend         - Start just frontend"
	@echo "  make test             - Run all tests"
	@echo "  make lint             - Check code quality"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy ENV=production  - Deploy to EC2"
	@echo "  make logs-ec2 INSTANCE=...  - Stream EC2 logs"
	@echo "  make restart-ec2 INSTANCE=... - Restart EC2"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          - Run migrations"

dev:
	@echo "🚀 Open 3 terminals:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"

backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm install && npm run dev

deploy:
	chmod +x scripts/deploy-to-ec2.sh
	./scripts/deploy-to-ec2.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/venv frontend/node_modules .coverage
