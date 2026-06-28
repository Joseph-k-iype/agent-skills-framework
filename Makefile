.PHONY: data data-down data-logs backend worker beat frontend migrate revision seed \
        test test-backend test-frontend lint fmt install

UV := uv run --python 3.12

# ── Data services (Postgres + FalkorDB run as Docker images) ──
data:
	docker compose up -d

data-down:
	docker compose down

data-logs:
	docker compose logs -f --tail=100

# ── Native processes (Python via uv / Node via npm) ──
backend:
	cd backend && $(UV) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && $(UV) celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

beat:
	cd backend && $(UV) celery -A app.tasks.celery_app beat --loglevel=info

frontend:
	cd frontend && npm run dev

install:
	cd backend && uv sync --python 3.12 --extra dev
	cd frontend && npm install

# ── Database ──
migrate:
	cd backend && $(UV) alembic upgrade head

revision:
	cd backend && $(UV) alembic revision --autogenerate -m "$(m)"

seed:
	cd backend && $(UV) python -m app.db.seed

# ── Tests ──
test: test-backend test-frontend

test-backend:
	cd backend && $(UV) --extra dev pytest -q

test-frontend:
	cd frontend && npm run test -- --run

# ── Quality ──
lint:
	cd backend && $(UV) --extra dev ruff check app && $(UV) --extra dev mypy app
	cd frontend && npm run lint

fmt:
	cd backend && $(UV) --extra dev ruff format app
