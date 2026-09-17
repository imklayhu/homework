.PHONY: install dev-api dev-web test-api test-web lint-web verify

install:
	cd apps/api && uv sync --python 3.12
	cd apps/web && npm install

dev-api:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

test-api:
	cd apps/api && uv run pytest -q

test-web:
	cd apps/web && npm test -- --run

lint-web:
	cd apps/web && npm run lint

verify: test-api lint-web
	cd apps/web && npm run build
