SHELL := /bin/bash
.PHONY: help sync test lint format typecheck check docker-setup docker-build docker-push docker-build-local

# --- configuration ---
PROJECT := cloudability-mcp-server
VERSION ?= $(shell grep -E '^version\s*=' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')
IMAGE_NAME ?= $(PROJECT)
IMAGE_TAG ?= $(VERSION)
REGISTRY ?=
PLATFORMS ?= linux/amd64,linux/arm64
DOCKERFILE ?= Dockerfile
BUILDER ?= $(PROJECT)-builder
UV ?= uv

ifdef REGISTRY
IMAGE := $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
else
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
endif

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync: ## Install runtime and dev dependencies with uv
	$(UV) sync --group dev

test: sync ## Run unit tests (integration tests excluded by default)
	$(UV) run pytest tests/

integration-test: sync ## Run integration tests
	$(UV) run pytest tests/test_mcp_integration.py -v -m integration

lint: sync ## Run Ruff linter
	$(UV) run ruff check .

format: sync ## Format code with Black and isort
	$(UV) run black .
	$(UV) run isort .

typecheck: sync ## Run mypy on application modules
	$(UV) run mypy main.py cloudability_tools.py cloudability_resources.py

check: lint typecheck test ## Run lint, typecheck, and tests

docker-setup: ## Create and bootstrap a buildx builder for multi-arch builds
	@docker buildx inspect $(BUILDER) >/dev/null 2>&1 || \
		docker buildx create --name $(BUILDER) --driver docker-container --use
	@docker buildx inspect --bootstrap >/dev/null

docker-build: docker-setup ## Build multi-arch image (set PUSH=1 to publish)
	docker buildx build \
		--builder $(BUILDER) \
		--platform $(PLATFORMS) \
		-f $(DOCKERFILE) \
		-t $(IMAGE) \
		--provenance=false \
		$(if $(PUSH),--push,) \
		.

docker-push: docker-setup ## Build multi-arch image and push to REGISTRY
	@test -n "$(REGISTRY)" || { echo "REGISTRY must be set, e.g. REGISTRY=ghcr.io/myorg"; exit 1; }
	$(MAKE) docker-build PUSH=1

docker-build-local: docker-setup ## Build and load image for the current machine only
	docker buildx build \
		--builder $(BUILDER) \
		--platform linux/$$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
		-f $(DOCKERFILE) \
		-t $(IMAGE) \
		--load \
		--provenance=false \
		.
