.PHONY: install dev-api dev-web test-api test-web test-e2e lint-web verify

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

test-e2e:
	cd apps/web && npm run test:e2e

lint-web:
	cd apps/web && npm run lint

verify: test-api test-web lint-web
	cd apps/web && npm run build
	$(MAKE) test-e2e
