PROTO_DIR := proto
SIMULATOR_DIR := simulator
SIMULATOR_PROTO_OUT := $(SIMULATOR_DIR)/proto_gen

.PHONY: proto
proto: proto-python

.PHONY: proto-python
proto-python:
	mkdir -p $(SIMULATOR_PROTO_OUT)
	cd $(SIMULATOR_DIR) && uv run python -m grpc_tools.protoc \
		-I ../$(PROTO_DIR) \
		--python_out=proto_gen \
		--pyi_out=proto_gen \
		../$(PROTO_DIR)/*.proto
	touch $(SIMULATOR_PROTO_OUT)/__init__.py
