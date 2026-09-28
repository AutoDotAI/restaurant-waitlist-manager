.DEFAULT_GOAL := help

.PHONY: help install backend-install frontend-install dev backend frontend test build

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "%-18s %s\n", $$1, $$2}'

install: backend-install frontend-install ## Install backend and frontend dependencies

backend-install: ## Install backend dependencies with uv
	cd backend && uv sync

frontend-install: ## Install frontend dependencies with npm
	cd frontend && npm ci

dev: ## Run the backend API and frontend dev server together
	$(MAKE) --jobs=2 backend frontend

backend: ## Run the FastAPI server at http://localhost:8000
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run the frontend dev server at http://localhost:3000
	cd frontend && npm run dev -- --host 0.0.0.0 --port 3000

test: ## Run backend tests
	cd backend && uv run pytest

build: ## Build the frontend for production
	cd frontend && npm run build
