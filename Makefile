.PHONY: build up down logs shell rebuild index ps clean

# ── Local dev ────────────────────────────────────────────────

build:
	docker compose build --no-cache

up:
	docker compose up -d
	@echo "Backend: http://localhost:80/api/health"

down:
	docker compose down

restart:
	docker compose restart backend

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-ollama:
	docker compose logs -f ollama

ps:
	docker compose ps

# ── Backend shell ────────────────────────────────────────────

shell:
	docker compose exec backend bash

# ── RAG index management ─────────────────────────────────────

index:
	docker compose exec backend python data_pipeline/pipeline.py
	docker compose exec backend python -c "\
	from core.rag import rag_system; \
	rag_system.initialise(force_rebuild=True); \
	print('Chunks indexed:', len(rag_system.chunks))"

# ── Production ───────────────────────────────────────────────

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# ── Cleanup ──────────────────────────────────────────────────

clean:
	docker compose down -v --remove-orphans
	docker image prune -f

clean-all:
	docker compose down -v --remove-orphans
	docker system prune -af --volumes