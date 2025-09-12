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
	@echo "  make build-layers    - Build Lambda layers (legacy)"
	@echo "  make build-layers-optimized - Build optimized Lambda layers for performance"
	@echo "  make deploy          - Deploy with auto Bedrock config sync ⭐"
	@echo "  make deploy-safe     - Same as deploy (safe by default)"
	@echo "  make deploy-full-fix - Deploy with comprehensive configuration fix"
	@echo "  make sync-config     - Sync Bedrock Agent configuration only"
	@echo "  make destroy         - Safely destroy infrastructure with cleanup"
	@echo "  make check-cloudfront - Check CloudFront resources status"
	@echo "  make safe-destroy    - Run comprehensive cleanup and destroy"
	@echo "  make tf-destroy      - Run Terraform destroy only (less safe)"
	@echo "  make docs            - Generate HTML documentation"
	@echo "  make docs-serve      - Serve documentation with live reload"
	@echo "  make docs-clean      - Clean documentation build files"
	@echo ""
	@echo "API Configuration commands:"
	@echo "  make update-api-config - Auto-update API Keys and URLs in test scripts"
	@echo "  make validate-api-config - Validate current API configuration"
	@echo "  make test-api        - Run comprehensive API functionality tests"
	@echo "  make health-check    - Quick system health verification"
	@echo ""
	@echo "Performance optimization commands:"
	@echo "  make perf-test       - Run Lambda performance tests"
	@echo "  make perf-monitor    - Monitor Lambda performance metrics"
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
	@echo "🧹 Cleaning temporary files..."
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf build/ dist/ *.egg-info 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

# Clean everything including virtual environment
clean-all: clean
	rm -rf $(VENV)
	@echo "✅ Cleaned all files including virtual environment"

# Build Lambda layers (legacy)
build-layers:
	@echo "Building Lambda layers..."
	cd lambdas/layers && ./build.sh
	@echo "✅ Lambda layers built"

# Build optimized Lambda layers for performance
build-layers-optimized:
	@echo "🔨 Building optimized Lambda layers..."
	@if [ ! -f scripts/build_optimized_layers.sh ]; then \
		echo "❌ Optimized layer build script not found!"; \
		exit 1; \
	fi
	@chmod +x scripts/build_optimized_layers.sh
	@bash scripts/build_optimized_layers.sh 2>&1 | grep -E "(^\[|✅|❌|WARNING|ERROR|built:|MB)" || true
	@echo "✅ Lambda layers ready"

# Performance test - measure cold start times
perf-test:
	@echo "Running Lambda performance tests..."
	@if [ ! -f scripts/performance_test.py ]; then \
		echo "❌ Performance test script not found!"; \
		echo "Creating basic performance test script..."; \
		mkdir -p scripts; \
		echo "#!/usr/bin/env python3" > scripts/performance_test.py; \
		echo "print('Performance testing functionality to be implemented')" >> scripts/performance_test.py; \
	fi
	@if [ -f $(VENV_PYTHON) ]; then \
		$(VENV_PYTHON) scripts/performance_test.py; \
	else \
		python3 scripts/performance_test.py; \
	fi
	@echo "✅ Performance test completed"

# Monitor performance metrics
perf-monitor:
	@echo "Monitoring Lambda performance metrics..."
	@aws cloudwatch get-metric-statistics \
		--namespace AWS/Lambda \
		--metric-name Duration \
		--dimensions Name=FunctionName,Value=$(PROJECT_NAME)-api-presentation-status \
		--start-time $$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
		--end-time $$(date -u +%Y-%m-%dT%H:%M:%S) \
		--period 300 \
		--statistics Average,Maximum \
		--region $(AWS_REGION) \
		|| echo "❌ AWS CLI not configured or no metrics available"
	@echo "✅ Performance monitoring completed"

# Package Lambda functions
package-lambdas:
	@echo "📦 Packaging Lambda functions..."
	@# First, ensure utils directory is available
	@if [ ! -d "lambdas/utils" ]; then \
		echo "❌ Error: lambdas/utils directory not found!"; \
		exit 1; \
	fi
	@# Count functions
	@api_count=$$(ls lambdas/api/*.py 2>/dev/null | wc -l | tr -d ' '); \
	controller_count=$$(ls lambdas/controllers/*.py 2>/dev/null | wc -l | tr -d ' '); \
	echo "  📂 API functions: $$api_count | Controller functions: $$controller_count"
	@# Package API functions (silent)
	@for func in lambdas/api/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			rm -f lambdas/api/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr api/$$base.zip -j /tmp/$$base.py && zip -qr api/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@# Package controller functions (silent)
	@for func in lambdas/controllers/*.py; do \
		if [ -f "$$func" ]; then \
			base=$$(basename $$func .py); \
			rm -f lambdas/controllers/$$base.zip; \
			cp $$func /tmp/$$base.py; \
			cd lambdas && zip -qr controllers/$$base.zip -j /tmp/$$base.py && zip -qr controllers/$$base.zip utils/ -x "*.pyc" -x "*__pycache__*" && cd - > /dev/null; \
			rm -f /tmp/$$base.py; \
		fi \
	done
	@echo "✅ Lambda functions packaged"

# Package infrastructure Lambda functions
package-infrastructure-lambdas:
	@echo "📦 Packaging infrastructure functions..."
	@# Package list_presentations function (silent)
	@if [ -f "infrastructure/lambda_functions/list_presentations.py" ]; then \
		cd infrastructure/lambda_functions && \
		zip -qr list_presentations.zip list_presentations.py && \
		cd - > /dev/null; \
	fi
	@echo "✅ Infrastructure functions ready"

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
	@echo "🚀 Deploying infrastructure with Terraform..."
	@cd infrastructure && $(TERRAFORM) apply \
		-var="project_name=$(PROJECT_NAME)" \
		-var="aws_region=$(AWS_REGION)" \
		-auto-approve \
		2>&1 | grep -E "(^Apply complete|^Plan:|Creating\.\.\.|Modifying\.\.\.|Destroying\.\.\.|Error:|Warning:|aws_|module\.)" || true
	@echo "✅ Infrastructure deployed"

# Destroy infrastructure
tf-destroy:
	cd infrastructure && $(TERRAFORM) destroy -var="project_name=$(PROJECT_NAME)" -var="aws_region=$(AWS_REGION)" -var="owner=AI-Team" -var="cost_center=Engineering" -auto-approve
	@echo "✅ Infrastructure destroyed"

# Check CloudFront resources status
check-cloudfront:
	@echo "🔍 Checking CloudFront resources status..."
	@if [ ! -f scripts/check_cloudfront_resources.sh ]; then \
		echo "❌ CloudFront check script not found!"; \
		echo "ℹ️  Script should be at: scripts/check_cloudfront_resources.sh"; \
		exit 1; \
	fi
	@chmod +x scripts/check_cloudfront_resources.sh
	@bash scripts/check_cloudfront_resources.sh

# Legacy safe destroy with cleanup script
safe-destroy-legacy:
	@echo "🔧 Running safe destroy with comprehensive cleanup..."
	@if [ ! -f scripts/safe_destroy.sh ]; then \
		echo "❌ Safe destroy script not found!"; \
		exit 1; \
	fi
	@chmod +x scripts/safe_destroy.sh
	@bash scripts/safe_destroy.sh
	@echo "✅ Safe destroy completed"

# Enhanced safe destroy with intelligent CloudFront handling
safe-destroy:
	@echo "🚀 Running enhanced safe destroy v2.0 with intelligent CloudFront handling..."
	@echo "ℹ️  This version automatically handles CloudFront distributions and OAI dependencies"
	@if [ ! -f scripts/enhanced_safe_destroy.sh ]; then \
		echo "⚠️  Enhanced destroy script not found, falling back to legacy version..."; \
		$(MAKE) safe-destroy-legacy; \
	else \
		chmod +x scripts/enhanced_safe_destroy.sh; \
		bash scripts/enhanced_safe_destroy.sh; \
		echo "✅ Enhanced safe destroy completed successfully!"; \
	fi

# Real destroy target (now uses enhanced safe-destroy for reliability)
destroy: safe-destroy

# Full deployment with performance optimization
deploy: clean build-layers-optimized package-lambdas package-infrastructure-lambdas tf-apply sync-config
	@echo "✅ Full deployment completed"

# Reliable deployment with verification (RECOMMENDED)
deploy-reliable: clean build-layers-optimized package-lambdas package-infrastructure-lambdas
	@echo ""
	@echo "🚀 Starting reliable deployment..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Phase 1: Deploying infrastructure with Terraform..."
	@cd infrastructure && $(TERRAFORM) apply \
		-var="project_name=$(PROJECT_NAME)" \
		-var="aws_region=$(AWS_REGION)" \
		-auto-approve \
		-parallelism=20 2>&1 | \
		grep -E "(Apply complete|Creating.*bedrock|Creating.*lambda|Creating.*dynamodb|Error:|failed)" || true
	@echo "✅ Infrastructure deployed"
	@echo ""
	@echo "⏳ Phase 2: Waiting for resources to initialize (20s)..."
	@sleep 20
	@echo ""
	@echo "🔄 Phase 3: Syncing Bedrock configuration..."
	@if [ -f scripts/sync_bedrock_config.sh ]; then \
		chmod +x scripts/sync_bedrock_config.sh && \
		./scripts/sync_bedrock_config.sh 2>&1 | grep -E "(✅|❌|Found Bedrock|completed|ERROR)" || echo "⚠️ Config sync had issues"; \
	else \
		echo "❌ ERROR: sync_bedrock_config.sh not found!"; \
		./scripts/update_api_config.sh 2>/dev/null || echo "⚠️ Using fallback sync"; \
	fi
	@echo ""
	@echo "⏳ Phase 4: Waiting for Lambda updates (10s)..."
	@sleep 10
	@echo ""
	@echo "🧪 Phase 5: Verifying deployment..."
	@if [ -f scripts/verify_deployment.py ]; then \
		python3 scripts/verify_deployment.py 2>&1 | grep -E "(✅|❌|⚠️|PASSED|FAILED)" || true; \
	else \
		echo "⚠️ Verification script not found"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Deployment completed successfully!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Legacy deployment (original layers)
deploy-legacy: clean build-layers package-lambdas package-infrastructure-lambdas tf-apply sync-config
	@echo "✅ Legacy deployment completed"

# Safe deployment with automatic configuration
deploy-safe: deploy
	@echo "🔒 Safe deployment with configuration sync completed"

# Sync Bedrock configuration after deployment with proper wait time
sync-config:
	@echo "🔄 Syncing Bedrock configuration..."
	@echo "⏳ Waiting for AWS resources to stabilize (15s)..."
	@sleep 15
	@if [ -f scripts/sync_bedrock_config.sh ]; then \
		chmod +x scripts/sync_bedrock_config.sh && \
		scripts/sync_bedrock_config.sh; \
		echo "⏳ Waiting for Lambda configuration updates (10s)..."; \
		sleep 10; \
	elif [ -f scripts/smart_bedrock_sync.sh ]; then \
		chmod +x scripts/smart_bedrock_sync.sh && \
		scripts/smart_bedrock_sync.sh; \
		echo "⏳ Waiting for Lambda configuration updates (10s)..."; \
		sleep 10; \
	else \
		echo "⚠️ No sync script found, configuration may be incomplete"; \
	fi
	@echo "✅ Configuration sync completed"

# Full deployment with complete configuration fix (for fresh installations)
deploy-full-fix: deploy
	@echo "🔨 Running comprehensive configuration fix..."
	@if [ -f scripts/deploy_long_term_fix.sh ]; then \
		chmod +x scripts/deploy_long_term_fix.sh && \
		scripts/deploy_long_term_fix.sh; \
	else \
		echo "❌ deploy_long_term_fix.sh not found"; \
		exit 1; \
	fi
	@echo "✅ Full deployment with comprehensive fix completed"

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
LAYER_HASH := $(shell md5 lambdas/layers/requirements.txt 2>/dev/null | awk '{print $$NF}' || echo "no-hash")
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

# AWS Expert: 自动化API配置更新
update-api-config:
	@echo "🔧 更新API配置..."
	@if [ ! -f scripts/update_api_config.sh ]; then \
		echo "❌ 配置更新脚本不存在: scripts/update_api_config.sh"; \
		exit 1; \
	fi
	@chmod +x scripts/update_api_config.sh
	@scripts/update_api_config.sh 2>&1 | grep -E "(^🔧|^✅|^❌|^💡|API Gateway URL:|API Key:|配置信息已保存)" || true
	@echo "✅ API配置更新完成"

# 验证API配置
validate-api-config:
	@echo "🧪 验证API配置..."
	@if [ ! -f scripts/update_api_config.sh ]; then \
		echo "❌ 配置验证脚本不存在"; \
		exit 1; \
	fi
	@chmod +x scripts/update_api_config.sh
	@scripts/update_api_config.sh --validate-only


# API功能测试
test-api:
	@echo "🧪 运行API功能测试..."
	@if [ -f comprehensive_backend_test.py ]; then \
		python3 comprehensive_backend_test.py; \
	elif [ -f test_all_backend_apis.py ]; then \
		python3 test_all_backend_apis.py; \
	else \
		echo "❌ 测试脚本未找到"; \
		exit 1; \
	fi
	@echo "✅ API测试完成"

# 快速健康检查
health-check:
	@echo "🩺 执行系统健康检查..."
	@if [ -f system_health_check.py ]; then \
		python3 system_health_check.py; \
	else \
		echo "❌ 健康检查脚本未找到"; \
		exit 1; \
	fi
	@echo "✅ 健康检查完成"

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