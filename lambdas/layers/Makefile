# Lambda Layer Build Makefile for AI PPT Assistant
# Supports Python 3.12 Lambda runtime compatibility

.PHONY: help clean build-docker build-local test verify deploy-layer install-deps

# Configuration
LAYER_NAME := ai-ppt-assistant-dependencies
PYTHON_VERSION := 3.12
ARCHITECTURE := arm64
BUILD_DIR := build
DIST_DIR := dist
DOCKER_BUILD_SCRIPT := docker-build.sh
LEGACY_BUILD_SCRIPT := build.sh
TEST_SCRIPT := test-layer.py

# Default target
help:
	@echo "Lambda Layer Build System"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo "  build-docker    Build layer using Docker (recommended for production)"
	@echo "  build-local     Build layer using local Python (development only)"
	@echo "  test           Test the built layer compatibility"
	@echo "  verify         Verify layer structure and dependencies"
	@echo "  clean          Clean build artifacts"
	@echo "  install-deps   Install development dependencies"
	@echo "  deploy-layer   Deploy layer to AWS Lambda"
	@echo "  all            Build (Docker), test, and verify"
	@echo ""
	@echo "Configuration:"
	@echo "  Layer Name:     $(LAYER_NAME)"
	@echo "  Python Version: $(PYTHON_VERSION)"
	@echo "  Architecture:   $(ARCHITECTURE)"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	rm -f Dockerfile.layer
	rm -f *.zip
	@echo "Clean completed"

# Install development dependencies
install-deps:
	@echo "Installing development dependencies..."
	pip install --upgrade pip
	pip install safety bandit pytest
	@echo "Development dependencies installed"

# Build layer using Docker (recommended)
build-docker: clean
	@echo "Building layer using Docker method..."
	@if [ ! -f $(DOCKER_BUILD_SCRIPT) ]; then \
		echo "Error: $(DOCKER_BUILD_SCRIPT) not found"; \
		exit 1; \
	fi
	chmod +x $(DOCKER_BUILD_SCRIPT)
	./$(DOCKER_BUILD_SCRIPT)
	@echo "Docker build completed"

# Build layer using local Python (development only)
build-local: clean
	@echo "Warning: Building with local Python may have compatibility issues"
	@echo "Recommended to use 'make build-docker' for production"
	@if [ ! -f $(LEGACY_BUILD_SCRIPT) ]; then \
		echo "Error: $(LEGACY_BUILD_SCRIPT) not found"; \
		exit 1; \
	fi
	chmod +x $(LEGACY_BUILD_SCRIPT)
	./$(LEGACY_BUILD_SCRIPT) --local
	@echo "Local build completed"

# Test layer compatibility
test:
	@echo "Testing layer compatibility..."
	@if [ ! -f $(TEST_SCRIPT) ]; then \
		echo "Error: $(TEST_SCRIPT) not found"; \
		exit 1; \
	fi
	chmod +x $(TEST_SCRIPT)
	python3 $(TEST_SCRIPT)
	@echo "Layer testing completed"

# Verify layer structure and size
verify:
	@echo "Verifying layer package..."
	@if [ ! -f $(DIST_DIR)/$(LAYER_NAME).zip ]; then \
		echo "Error: Layer package not found. Run 'make build-docker' first"; \
		exit 1; \
	fi
	@echo "Layer package: $(DIST_DIR)/$(LAYER_NAME).zip"
	@ls -lh $(DIST_DIR)/$(LAYER_NAME).zip
	@echo ""
	@echo "Package contents (first 20 entries):"
	@unzip -l $(DIST_DIR)/$(LAYER_NAME).zip | head -25
	@echo ""
	@echo "Checking for required packages:"
	@unzip -l $(DIST_DIR)/$(LAYER_NAME).zip | grep -E "(boto3|aws_lambda_powertools|pptx|PIL)" || echo "Warning: Some required packages not found"
	@echo "Verification completed"

# Security scan
security-scan:
	@echo "Running security scan..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check -r requirements.txt; \
	else \
		echo "Installing safety..."; \
		pip install safety; \
		safety check -r requirements.txt; \
	fi
	@echo "Security scan completed"

# Deploy layer to AWS Lambda
deploy-layer:
	@echo "Deploying layer to AWS Lambda..."
	@if [ ! -f $(DIST_DIR)/$(LAYER_NAME).zip ]; then \
		echo "Error: Layer package not found. Run 'make build-docker' first"; \
		exit 1; \
	fi
	@if ! command -v aws >/dev/null 2>&1; then \
		echo "Error: AWS CLI not found. Please install AWS CLI"; \
		exit 1; \
	fi
	aws lambda publish-layer-version \
		--layer-name $(LAYER_NAME) \
		--description "Shared dependencies for AI PPT Assistant (Docker built)" \
		--zip-file fileb://$(DIST_DIR)/$(LAYER_NAME).zip \
		--compatible-runtimes python$(PYTHON_VERSION) \
		--compatible-architectures $(ARCHITECTURE) \
		--query '{LayerVersionArn: LayerVersionArn, Version: Version}' \
		--output table
	@echo "Layer deployment completed"

# List existing layer versions
list-layers:
	@echo "Listing existing layer versions..."
	@if ! command -v aws >/dev/null 2>&1; then \
		echo "Error: AWS CLI not found. Please install AWS CLI"; \
		exit 1; \
	fi
	aws lambda list-layer-versions \
		--layer-name $(LAYER_NAME) \
		--query 'LayerVersions[?CompatibleRuntimes[?contains(@, `python$(PYTHON_VERSION)`)]].[Version, Description, CreatedDate]' \
		--output table

# Docker system cleanup
docker-cleanup:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker images | grep "$(LAYER_NAME)-builder" | awk '{print $3}' | xargs -r docker rmi
	@echo "Docker cleanup completed"

# Full build, test, and verify pipeline
all: build-docker test verify
	@echo ""
	@echo "========================="
	@echo "Full pipeline completed!"
	@echo "========================="
	@echo ""
	@echo "Next steps:"
	@echo "1. Review test results above"
	@echo "2. Run 'make deploy-layer' to deploy to AWS"
	@echo "3. Update your Lambda functions to use the new layer"

# Development workflow
dev: install-deps build-local test
	@echo "Development build completed"

# Production workflow  
prod: install-deps security-scan build-docker test verify
	@echo "Production build completed and verified"
	@echo "Ready for deployment with 'make deploy-layer'"

# Show layer info
info:
	@echo "Layer Information"
	@echo "=================="
	@echo "Name: $(LAYER_NAME)"
	@echo "Python Version: $(PYTHON_VERSION)"  
	@echo "Architecture: $(ARCHITECTURE)"
	@echo "Build Directory: $(BUILD_DIR)"
	@echo "Distribution Directory: $(DIST_DIR)"
	@echo ""
	@if [ -f $(DIST_DIR)/$(LAYER_NAME).zip ]; then \
		echo "Layer package exists: $(DIST_DIR)/$(LAYER_NAME).zip"; \
		ls -lh $(DIST_DIR)/$(LAYER_NAME).zip; \
	else \
		echo "Layer package not found. Run 'make build-docker' to create it."; \
	fi
	@echo ""
	@if [ -f $(DIST_DIR)/layer-metadata.json ]; then \
		echo "Metadata:"; \
		cat $(DIST_DIR)/layer-metadata.json; \
	fi