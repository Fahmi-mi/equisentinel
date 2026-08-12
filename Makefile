MIGRATIONS_DIR := migrations
POSTGRES_USER ?= equisentinel
POSTGRES_DB ?= equisentinel

PROTO_DIR := proto
SIMULATOR_DIR := simulator
SIMULATOR_PROTO_OUT := $(SIMULATOR_DIR)/proto_gen
AI_WORKER_DIR := ai-worker
AI_WORKER_PROTO_OUT := $(AI_WORKER_DIR)/proto_gen
GATEWAY_DIR := gateway
GATEWAY_PROTO_OUT := $(GATEWAY_DIR)/internal/proto
DASHBOARD_DIR := dashboard

.PHONY: proto
proto: proto-python proto-ai-worker proto-go

.PHONY: proto-python
proto-python:
	mkdir -p $(SIMULATOR_PROTO_OUT)
	cd $(SIMULATOR_DIR) && uv run python -m grpc_tools.protoc \
		-I ../$(PROTO_DIR) \
		--python_out=proto_gen \
		--pyi_out=proto_gen \
		../$(PROTO_DIR)/*.proto
	touch $(SIMULATOR_PROTO_OUT)/__init__.py

.PHONY: proto-ai-worker
proto-ai-worker:
	mkdir -p $(AI_WORKER_PROTO_OUT)
	cd $(AI_WORKER_DIR) && uv run python -m grpc_tools.protoc \
		-I ../$(PROTO_DIR) \
		--python_out=proto_gen \
		--pyi_out=proto_gen \
		../$(PROTO_DIR)/*.proto
	touch $(AI_WORKER_PROTO_OUT)/__init__.py

.PHONY: proto-go
proto-go:
	mkdir -p $(GATEWAY_PROTO_OUT)
	protoc \
		-I $(PROTO_DIR) \
		--go_out=$(GATEWAY_PROTO_OUT) \
		--go_opt=paths=source_relative \
		$(PROTO_DIR)/*.proto

.PHONY: migrate
migrate:
	@docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \
		"CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());" > /dev/null
	@for f in $(MIGRATIONS_DIR)/*.sql; do \
		name=$$(basename $$f); \
		applied=$$(docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -tAc "SELECT 1 FROM schema_migrations WHERE filename = '$$name'"); \
		if [ "$$applied" = "1" ]; then \
			echo "skipping $$f (already applied)"; \
			continue; \
		fi; \
		echo "applying $$f"; \
		docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) < $$f; \
		docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \
			"INSERT INTO schema_migrations (filename) VALUES ('$$name')" > /dev/null; \
	done

.PHONY: up
up:
	docker compose up -d

.PHONY: down
down:
	docker compose down

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: test
test: test-gateway test-simulator test-ai-worker test-dashboard

.PHONY: test-gateway
test-gateway:
	cd $(GATEWAY_DIR) && go test ./...

.PHONY: test-simulator
test-simulator:
	cd $(SIMULATOR_DIR) && uv run pytest

.PHONY: test-ai-worker
test-ai-worker:
	cd $(AI_WORKER_DIR) && uv run pytest

.PHONY: test-dashboard
test-dashboard:
	cd $(DASHBOARD_DIR) && npx vitest run

.PHONY: test-integration
test-integration:
	docker compose up -d --wait
	$(MAKE) migrate
	docker compose exec -T ai-worker python scripts/full_stack_integration_test.py
