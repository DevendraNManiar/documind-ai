.PHONY: up down api worker test lint fmt

up:
	docker compose up --build

down:
	docker compose down

api:
	uvicorn app.main:app --reload

worker:
	celery -A app.workers.celery_app.celery worker --loglevel=info

test:
	pytest -q

lint:
	ruff check app tests

fmt:
	ruff format app tests
