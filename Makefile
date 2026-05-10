.PHONY: help dev dev-backend dev-frontend docker-up docker-down migrate seed test lint format

help:
	@echo "ImmoManager - Swiss Property Management Platform"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev            - Start full stack (Docker)"
	@echo "  make dev-backend    - Start Django dev server"
	@echo "  make dev-frontend   - Start Next.js dev server"
	@echo "  make docker-up      - Start all Docker services"
	@echo "  make docker-down    - Stop all Docker services"
	@echo "  make migrate        - Run Django migrations"
	@echo "  make seed           - Seed database with sample data"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"

dev:
	docker compose up

dev-backend:
	cd backend && python manage.py runserver

dev-frontend:
	cd frontend && npm run dev

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-rebuild:
	docker compose down && docker compose build --no-cache && docker compose up

migrate:
	cd backend && python manage.py migrate

makemigrations:
	cd backend && python manage.py makemigrations

seed:
	cd backend && python manage.py seed_data

superuser:
	cd backend && python manage.py createsuperuser

shell:
	cd backend && python manage.py shell

test-backend:
	cd backend && python manage.py test

test-frontend:
	cd frontend && npm run test

test: test-backend test-frontend

lint-backend:
	cd backend && flake8 . --max-line-length=120

lint-frontend:
	cd frontend && npm run lint

lint: lint-backend lint-frontend

format-backend:
	cd backend && black . && isort .

format-frontend:
	cd frontend && npx prettier --write .

format: format-backend format-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install: install-backend install-frontend

export-requirements:
	cd backend && pip freeze > requirements.txt
