# Makefile for AI PPT Assistant

.PHONY: help venv install test test-unit test-integration test-e2e lint format clean clean-all deploy docs docs-serve docs-clean docs-api docs-full security-install security-scan security-scan-ci security-report

# Variables
PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
BLACK := $(VENV)/bin/black
FLAKE8 := $(VENV)/bin/flake8
SPHINX_BUILD := $(VENV)/bin/sphinx-build
SPHINX_AUTOBUILD := $(VENV)/bin/sphinx-autobuild
TERRAFORM := terraform
AWS_REGION := us-east-1
PROJECT_NAME := ai-ppt-assistant

# Default target
help:
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies (creates venv if needed)"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e        - Run end-to-end tests only"
	@echo "  make lint            - Run code linting"
	@echo "  make format          - Format code with black"
	@echo "  make clean           - Clean up temporary files"
	@echo "  make clean-all       - Clean everything including virtual environment"
	@echo "  make build-layers    - Build Lambda layers"
	@echo "  make deploy          - Deploy infrastructure with Terraform"
	@echo "  make destroy         - Safely destroy infrastructure with cleanup"
	@echo "  make safe-destroy    - Run comprehensive cleanup and destroy"
	@echo "  make tf-destroy      - Run Terraform destroy only (less safe)"
	@echo "  make docs            - Generate HTML documentation"
	@echo "  make docs-serve      - Serve documentation with live reload"
	@echo "  make docs-clean      - Clean documentation build files"
	@echo ""
	@echo "Security commands:"
	@echo "  make security-install - Install security scanning tools"
	@echo "  make security-scan    - Run comprehensive security scan"
	@echo "  make security-scan-ci - Run security scan for CI/CD (fails on high/critical)"
	@echo "  make security-report  - Generate detailed HTML security report"

# Create virtual environment if it doesn't exist
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
	fi

# Install dependencies
install: venv
	$(VENV_PIP) install --upgrade pip
	@if [ -f tests/requirements.txt ]; then \
		$(VENV_PIP) install -r tests/requirements.txt; \
	fi
	@if [ -f lambdas/layers/requirements.txt ]; then \
		$(VENV_PIP) install -r lambdas/layers/requirements.txt; \
	fi
	@if [ -f docs/requirements.txt ]; then \
		$(VENV_PIP) install -r docs/requirements.txt; \
	fi
	@echo "✅ Dependencies installed in virtual environment"

# Run all tests
test: lint test-unit test-integration
	@echo "✅ All tests completed"

# Run unit tests
test-unit: venv
	@echo "Running unit tests..."
	@if [ -f $(VENV)/bin/pytest ]; then \
		$(PYTEST) tests/unit -v --cov=lambdas --cov-report=term-missing --cov-report=html; \
	else \
		echo "⚠️  pytest not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ Unit tests completed. Coverage report: htmlcov/index.html"

# Run integration tests
test-integration: venv
	@echo "Running integration tests..."
	@if [ -f $(VENV)/bin/pytest ]; then \
		$(PYTEST) tests/integration -v -m integration; \
	else \
		echo "⚠️  pytest not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ Integration tests completed"

# Run end-to-end tests
test-e2e: venv
	@echo "Running end-to-end tests..."
	@if [ -f $(VENV)/bin/pytest ]; then \
		$(PYTEST) tests/e2e -v -m e2e --timeout=180; \
	else \
		echo "⚠️  pytest not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ End-to-end tests completed"

# Run smoke tests
test-smoke: venv
	@echo "Running smoke tests..."
	@if [ -f $(VENV)/bin/pytest ]; then \
		$(PYTEST) tests -v -m smoke -x; \
	else \
		echo "⚠️  pytest not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ Smoke tests completed"

# Lint code
lint: venv
	@echo "Running code linting..."
	@if [ -f $(VENV)/bin/flake8 ]; then \
		$(VENV)/bin/flake8 lambdas --max-line-length=120 --exclude=__pycache__,venv,.venv || true; \
	else \
		echo "⚠️  flake8 not installed. Run 'make install' first."; \
	fi
	@if [ -f $(VENV)/bin/black ]; then \
		$(VENV)/bin/black lambdas --check --diff || true; \
	else \
		echo "⚠️  black not installed. Run 'make install' first."; \
	fi
	@echo "✅ Linting completed"

# Format code
format: venv
	@echo "Formatting code..."
	@if [ -f $(VENV)/bin/black ]; then \
		$(VENV)/bin/black lambdas; \
	else \
		echo "⚠️  black not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ Code formatted"

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	rm -rf build/ dist/ *.egg-info
	@echo "✅ Cleaned temporary files"

# Clean everything including virtual environment
clean-all: clean
	rm -rf $(VENV)
	@echo "✅ Cleaned all files including virtual environment"

# Build Lambda layers
build-layers:
	@echo "Building Lambda layers..."
	cd lambdas/layers && ./build.sh
	@echo "✅ Lambda layers built"

# Package Lambda functions
package-lambdas:
	@echo "Packaging Lambda functions with utils..."
	@# First, ensure utils directory is available
	@if [ ! -d "lambdas/utils" ]; then \
		echo "❌ Error: lambdas/utils directory not found!"; \
		exit 1; \
	fi
	@# Package API functions
	@for func in lambdas/api/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			echo "Packaging API function: $$base..."; \
			rm -f lambdas/api/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr api/$$base.zip -j /tmp/$$base.py && zip -qr api/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@# Package controller functions
	@for func in lambdas/controllers/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			echo "Packaging controller function: $$base..."; \
			rm -f lambdas/controllers/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr controllers/$$base.zip -j /tmp/$$base.py && zip -qr controllers/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@echo "✅ Lambda functions packaged with utils"

# Package infrastructure Lambda functions
package-infrastructure-lambdas:
	@echo "Packaging infrastructure Lambda functions..."
	@# Package list_presentations function
	@if [ -f "infrastructure/lambda_functions/list_presentations.py" ]; then \
		echo "Packaging list_presentations function..."; \
		cd infrastructure/lambda_functions && \
		zip -qr list_presentations.zip list_presentations.py && \
		cd - > /dev/null; \
		echo "✅ list_presentations function packaged"; \
	fi
	@# Package any other infrastructure Lambda functions here
	@echo "✅ Infrastructure Lambda functions packaged"

# Initialize Terraform
tf-init:
	cd infrastructure && $(TERRAFORM) init
	@echo "✅ Terraform initialized"

# Plan Terraform changes
tf-plan:
	cd infrastructure && $(TERRAFORM) plan -var="project_name=$(PROJECT_NAME)" -var="aws_region=$(AWS_REGION)"
	@echo "✅ Terraform plan generated"

# Apply Terraform changes
tf-apply:
	cd infrastructure && $(TERRAFORM) apply -var="project_name=$(PROJECT_NAME)" -var="aws_region=$(AWS_REGION)" -auto-approve
	@echo "✅ Infrastructure deployed"

# Destroy infrastructure
tf-destroy:
	cd infrastructure && $(TERRAFORM) destroy -var="project_name=$(PROJECT_NAME)" -var="aws_region=$(AWS_REGION)" -auto-approve
	@echo "✅ Infrastructure destroyed"

# Safe destroy with cleanup script
safe-destroy:
	@echo "🔧 Running safe destroy with comprehensive cleanup..."
	@if [ ! -f scripts/safe_destroy.sh ]; then \
		echo "❌ Safe destroy script not found!"; \
		exit 1; \
	fi
	@chmod +x scripts/safe_destroy.sh
	@bash scripts/safe_destroy.sh
	@echo "✅ Safe destroy completed"

# Real destroy target (now uses safe-destroy for reliability)
destroy: safe-destroy

# Protection against common typos for destroy command
desotry:
	@echo "❌ Error: 'make desotry' is not a valid command!"
	@echo "📝 Did you mean: 'make destroy'?"
	@echo "⚠️  Please use the correct spelling to avoid accidental execution."
	@exit 1

destory:
	@echo "❌ Error: 'make destory' is not a valid command!"
	@echo "📝 Did you mean: 'make destroy'?"
	@echo "⚠️  Please use the correct spelling to avoid accidental execution."
	@exit 1

detroy:
	@echo "❌ Error: 'make detroy' is not a valid command!"
	@echo "📝 Did you mean: 'make destroy'?"
	@echo "⚠️  Please use the correct spelling to avoid accidental execution."
	@exit 1

destry:
	@echo "❌ Error: 'make destry' is not a valid command!"
	@echo "📝 Did you mean: 'make destroy'?"
	@echo "⚠️  Please use the correct spelling to avoid accidental execution."
	@exit 1

# Full deployment
deploy: clean build-layers package-lambdas package-infrastructure-lambdas tf-apply
	@echo "✅ Full deployment completed"

# Validate everything
validate: lint test-unit
	cd infrastructure && $(TERRAFORM) validate
	@echo "✅ Validation completed"

# Install security scanning tools
security-install:
	@echo "Installing security scanning tools..."
	@if [ ! -f security/install.sh ]; then \
		echo "❌ Security installation script not found"; \
		exit 1; \
	fi
	@bash security/install.sh
	@echo "✅ Security tools installation completed"

# Run comprehensive security scan
security-scan: venv
	@echo "Running comprehensive security scan..."
	@if [ ! -f $(VENV)/bin/python ]; then \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@if [ ! -f security/scan.py ]; then \
		echo "⚠️  Security scanner not found. Run 'make security-install' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) security/scan.py --scan all --format console
	@echo "✅ Security scan completed"

# Run security scan for CI/CD (fails on high/critical issues)
security-scan-ci: venv
	@echo "Running security scan for CI/CD..."
	@if [ ! -f $(VENV)/bin/python ]; then \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@if [ ! -f security/scan.py ]; then \
		echo "⚠️  Security scanner not found. Run 'make security-install' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) security/scan.py --scan all --format json --fail-on-high
	@echo "✅ Security CI scan completed"

# Generate detailed HTML security report
security-report: venv
	@echo "Generating detailed security report..."
	@if [ ! -f $(VENV)/bin/python ]; then \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@if [ ! -f security/scan.py ]; then \
		echo "⚠️  Security scanner not found. Run 'make security-install' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) security/scan.py --scan all --format html
	@echo "✅ Security report generated. Check security/reports/ directory"

# Generate documentation
docs: venv
	@echo "Generating documentation..."
	@if [ -f $(SPHINX_BUILD) ]; then \
		$(SPHINX_BUILD) -b html docs/source docs/build/html; \
		echo "📚 Documentation generated at docs/build/html/index.html"; \
	else \
		echo "⚠️  Sphinx not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ Documentation generated"

# Serve documentation with live reload
docs-serve: venv
	@echo "Starting documentation server with live reload..."
	@if [ -f $(SPHINX_AUTOBUILD) ]; then \
		$(SPHINX_AUTOBUILD) docs/source docs/build/html --host 0.0.0.0 --port 8000; \
	else \
		echo "⚠️  sphinx-autobuild not installed. Run 'make install' first."; \
		exit 1; \
	fi

# Clean documentation build files
docs-clean:
	@echo "Cleaning documentation build files..."
	rm -rf docs/build/
	find docs/source/api -name "*.rst" -not -name "lambdas.rst" -delete
	@echo "✅ Documentation build files cleaned"

# Rebuild API documentation
docs-api: venv
	@echo "Rebuilding API documentation..."
	@if [ -f $(VENV)/bin/sphinx-apidoc ]; then \
		$(VENV)/bin/sphinx-apidoc -f -o docs/source/api lambdas --separate; \
		echo "📋 API documentation rebuilt"; \
	else \
		echo "⚠️  sphinx-apidoc not installed. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "✅ API documentation rebuilt"

# Build documentation with fresh API docs
docs-full: docs-clean docs-api docs
	@echo "✅ Full documentation build completed"

# Show project statistics
stats:
	@echo "Project Statistics:"
	@echo "==================="
	@find lambdas -name "*.py" | wc -l | xargs echo "Python files:"
	@find tests -name "test_*.py" | wc -l | xargs echo "Test files:"
	@find infrastructure -name "*.tf" | wc -l | xargs echo "Terraform files:"
	@find . -name "*.py" -exec wc -l {} + | tail -1 | awk '{print "Total Python LOC:", $$1}'

# CI/CD helpers
ci-test: install lint test-unit test-integration
	@echo "✅ CI tests completed"

cd-deploy: validate deploy
	@echo "✅ CD deployment completed"# Optimized Makefile additions for faster deployment

# Cache directory for Lambda layers
LAYER_CACHE := .layer-cache
LAYER_HASH := $(shell md5 lambdas/layers/requirements.txt 2>/dev/null || echo "no-hash")
CACHED_LAYER := $(LAYER_CACHE)/$(LAYER_HASH).zip

# Fast deployment (skip unnecessary steps)
fast-deploy: check-layer-cache package-lambdas-parallel tf-apply-parallel
	@echo "✅ Fast deployment completed"

# Check and use cached layer if requirements haven't changed
check-layer-cache:
	@if [ -f "$(CACHED_LAYER)" ]; then \
		echo "✅ Using cached Lambda layer from $(CACHED_LAYER)"; \
		cp $(CACHED_LAYER) lambdas/layers/dist/ai-ppt-assistant-dependencies.zip; \
	else \
		echo "📦 Building new Lambda layer..."; \
		$(MAKE) build-layers; \
		mkdir -p $(LAYER_CACHE); \
		cp lambdas/layers/dist/ai-ppt-assistant-dependencies.zip $(CACHED_LAYER); \
	fi

# Parallel Lambda packaging
package-lambdas-parallel:
	@echo "Packaging Lambda functions in parallel..."
	@# Package API functions in parallel
	@for func in lambdas/api/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			( \
				echo "Packaging API function: $$base..."; \
				rm -f lambdas/api/$$base.zip; \
				cp $$func /tmp/$$base.py; \
				cd lambdas && zip -qr api/$$base.zip -j /tmp/$$base.py && \
				zip -qr api/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && \
				cd - > /dev/null; \
				rm -f /tmp/$$base.py; \
				echo "✅ $$base packaged"; \
			) & \
		fi \
	done; \
	wait
	@# Package controller functions in parallel
	@for func in lambdas/controllers/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			( \
				echo "Packaging controller function: $$base..."; \
				rm -f lambdas/controllers/$$base.zip; \
				cp $$func /tmp/$$base.py; \
				cd lambdas && zip -qr controllers/$$base.zip -j /tmp/$$base.py && \
				zip -qr controllers/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && \
				cd - > /dev/null; \
				rm -f /tmp/$$base.py; \
				echo "✅ $$base packaged"; \
			) & \
		fi \
	done; \
	wait
	@echo "✅ All Lambda functions packaged in parallel"

# Terraform apply with parallelism
tf-apply-parallel:
	cd infrastructure && $(TERRAFORM) apply \
		-var="project_name=$(PROJECT_NAME)" \
		-var="aws_region=$(AWS_REGION)" \
		-parallelism=20 \
		-auto-approve
	@echo "✅ Infrastructure deployed with parallelism"

# Skip test Lambda functions in production deployment
package-lambdas-prod:
	@echo "Packaging production Lambda functions only..."
	@for func in lambdas/api/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			echo "Packaging API function: $$base..."; \
			rm -f lambdas/api/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr api/$$base.zip -j /tmp/$$base.py && zip -qr api/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@for func in lambdas/controllers/*.py; do \
		if [ -f "$$func" ] && [[ ! "$$func" =~ "test_" ]]; then \
			base=$$(basename $$func .py); \
			echo "Packaging controller function: $$base..."; \
			rm -f lambdas/controllers/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr controllers/$$base.zip -j /tmp/$$base.py && zip -qr controllers/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@echo "✅ Production Lambda functions packaged"

# Production deployment (skip test functions)
deploy-prod: clean check-layer-cache package-lambdas-prod package-infrastructure-lambdas tf-apply-parallel
	@echo "✅ Production deployment completed"

# Incremental deployment (only changed functions)
deploy-incremental:
	@echo "Detecting changed Lambda functions..."
	@git diff --name-only HEAD lambdas/ | grep -E '\.py$$' | while read file; do \
		if [[ "$$file" =~ lambdas/(api|controllers)/(.+)\.py ]]; then \
			dir=$$(dirname $$file); \
			base=$$(basename $$file .py); \
			echo "Repackaging changed function: $$base"; \
			rm -f $$dir/$$base.zip; \
			cp $$file /tmp/$$base.py; \
			cd lambdas && zip -qr $${dir#lambdas/}/$$base.zip -j /tmp/$$base.py && \
			zip -qr $${dir#lambdas/}/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && \
			cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	cd infrastructure && $(TERRAFORM) apply \
		-var="project_name=$(PROJECT_NAME)" \
		-var="aws_region=$(AWS_REGION)" \
		-parallelism=20 \
		-target=module.lambda \
		-auto-approve
	@echo "✅ Incremental deployment completed"

# Clean layer cache
clean-layer-cache:
	rm -rf $(LAYER_CACHE)
	@echo "✅ Layer cache cleaned"

# Docker-based layer build (ensures Python 3.12 compatibility)
build-layers-docker:
	@echo "Building Lambda layer with Docker (Python 3.12)..."
	docker run --rm \
		-v $$(pwd)/lambdas/layers:/var/task \
		-w /var/task \
		public.ecr.aws/lambda/python:3.12 \
		/bin/bash -c " \
			pip install --target python/lib/python3.12/site-packages -r requirements.txt && \
			zip -r dist/ai-ppt-assistant-dependencies.zip python/ \
		"
	@echo "✅ Lambda layer built with Docker"

# Help for optimized commands
help-optimize:
	@echo "Optimized deployment commands:"
	@echo "  make fast-deploy      - Fast deployment with caching and parallelism"
	@echo "  make deploy-prod      - Production deployment (skip test functions)"
	@echo "  make deploy-incremental - Deploy only changed Lambda functions"
	@echo "  make build-layers-docker - Build layers with Docker for compatibility"
	@echo "  make clean-layer-cache - Clean the layer cache"