PROTO_DIR := proto
SIMULATOR_DIR := simulator
SIMULATOR_PROTO_OUT := $(SIMULATOR_DIR)/proto_gen
AI_WORKER_DIR := ai-worker
AI_WORKER_PROTO_OUT := $(AI_WORKER_DIR)/proto_gen
GATEWAY_DIR := gateway
GATEWAY_PROTO_OUT := $(GATEWAY_DIR)/internal/proto

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
