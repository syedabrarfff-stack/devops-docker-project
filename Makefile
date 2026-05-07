.PHONY: up down logs build dev backend frontend

# Full stack
up:
	cd infrastructure && docker compose up -d

down:
	cd infrastructure && docker compose down

build:
	cd infrastructure && docker compose build --no-cache

logs:
	cd infrastructure && docker compose logs -f

restart:
	cd infrastructure && docker compose restart

# Individual
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Dev setup
dev-install:
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

status:
	cd infrastructure && docker compose ps
