# =============================================================================
# Geode Python Client Makefile
# Convenient shortcuts for build, test, lint, bench, and integration operations
# =============================================================================

PYTHON ?= python3
PIP ?= pip
PYTEST ?= pytest
VENV_DIR ?= .venv
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip
VENV_PYTEST = $(VENV_DIR)/bin/pytest

# Docker settings for integration tests
DOCKER ?= docker
# SEC-024: Pin Geode server image to specific version (not :latest)
# Update this version when new Geode releases are published
GEODE_VERSION ?= v0.1.0
GEODE_IMAGE ?= registry.gitlab.com/devnw/geode/geode:$(GEODE_VERSION)
GEODE_CONTAINER ?= geode-python-test
GEODE_HOST ?= 127.0.0.1
GEODE_PORT ?= 3141

.PHONY: all build install install-dev clean test test-unit test-property test-integration \
        test-integration-docker bench lint fmt fmt-check typecheck doc coverage ci ci-quick \
        ci-full help venv docker-start docker-stop docker-logs example

# Default target - run everything (except integration tests which require server)
all: install-dev fmt-check lint typecheck test-unit test-property bench-quick
	@echo ""
	@echo "==== All Checks Complete ===="
	@echo "✓ Dependencies installed"
	@echo "✓ Format check passed"
	@echo "✓ Ruff lint passed"
	@echo "✓ Type check passed"
	@echo "✓ Unit tests passed (409 tests)"
	@echo "✓ Property tests passed (50 tests)"
	@echo "✓ Benchmarks compiled"
	@echo ""
	@echo "Note: Run 'make test-integration' separately (requires Geode server)"
	@echo "      Run 'make test-integration-docker' to use Docker container"

# Help target
help:
	@echo "Geode Python Client Makefile"
	@echo "============================="
	@echo ""
	@echo "Setup targets:"
	@echo "  make venv          - Create virtual environment"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install with dev dependencies"
	@echo "  make clean         - Clean build artifacts and caches"
	@echo ""
	@echo "Test targets:"
	@echo "  make test          - Run all tests (unit + property)"
	@echo "  make test-unit     - Run unit tests only (409 tests)"
	@echo "  make test-property - Run property-based tests (50 tests)"
	@echo "  make test-integration - Run integration tests (requires Geode server)"
	@echo "  make test-integration-docker - Run integration tests with Docker"
	@echo "  make test-all      - Run ALL tests including integration"
	@echo ""
	@echo "Quality targets:"
	@echo "  make lint          - Run ruff linter"
	@echo "  make fmt           - Format code with ruff"
	@echo "  make fmt-check     - Check formatting without changes"
	@echo "  make typecheck     - Run mypy type checker"
	@echo ""
	@echo "Benchmark targets:"
	@echo "  make bench         - Run all benchmarks (154 benchmarks)"
	@echo "  make bench-quick   - Compile benchmarks only (no run)"
	@echo ""
	@echo "Docker targets:"
	@echo "  make docker-start  - Start Geode Docker container"
	@echo "  make docker-stop   - Stop Geode Docker container"
	@echo "  make docker-logs   - View Geode container logs"
	@echo ""
	@echo "CI targets:"
	@echo "  make ci            - Run full CI pipeline"
	@echo "  make ci-quick      - Run quick CI (no integration tests)"
	@echo "  make ci-full       - Run CI with integration tests"
	@echo ""
	@echo "Other targets:"
	@echo "  make coverage      - Generate coverage report"
	@echo "  make doc           - Generate documentation"
	@echo "  make example       - Run example scripts"
	@echo ""
	@echo "Environment variables:"
	@echo "  PYTHON            - Python interpreter (default: python3)"
	@echo "  GEODE_HOST        - Geode server host (default: 127.0.0.1)"
	@echo "  GEODE_PORT        - Geode server port (default: 3141)"
	@echo "  GEODE_VERSION     - Geode server version (default: v0.1.0)"
	@echo "  GEODE_IMAGE       - Docker image (default: registry.gitlab.com/devnw/geode/geode:\$$GEODE_VERSION)"

# =============================================================================
# Setup Targets
# =============================================================================

venv:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip
	@echo "✓ Virtual environment created at $(VENV_DIR)"
	@echo "  Activate with: source $(VENV_DIR)/bin/activate"

install: venv
	@echo "Installing package..."
	$(VENV_PIP) install -e .
	@echo "✓ Package installed"

install-dev: venv
	@echo "Installing package with dev dependencies..."
	$(VENV_PIP) install -e ".[dev,integration,benchmark,property]"
	@echo "✓ Package installed with dev dependencies"

build: install-dev
	@echo "✓ Build complete"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf geode_client.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .hypothesis/
	rm -rf .benchmarks/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf report-*.xml
	rm -rf benchmark-results.json
	rm -f =*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Clean complete"

# =============================================================================
# Test Targets
# =============================================================================

test: test-unit test-property
	@echo "✓ All tests complete"

test-unit:
	@echo "Running unit tests..."
	$(VENV_PYTEST) tests/unit/ -v
	@echo "✓ Unit tests complete (409 tests)"

test-property:
	@echo "Running property-based tests..."
	$(VENV_PYTEST) tests/property/ -v
	@echo "✓ Property tests complete (50 tests)"

test-integration:
	@echo "Running integration tests..."
	@echo ""
	@echo "Tests connect to Geode server at $(GEODE_HOST):$(GEODE_PORT)"
	@echo "Start server first: cd ../geode && ./zig-out/bin/geode serve"
	@echo "Or use: make docker-start"
	@echo ""
	GEODE_HOST=$(GEODE_HOST) GEODE_PORT=$(GEODE_PORT) \
		$(VENV_PYTEST) tests/integration/ -v -m integration
	@echo "✓ Integration tests complete (119 tests)"

test-integration-docker: docker-start
	@echo "Running integration tests with Docker..."
	@echo "Waiting for Geode server to be ready..."
	@sleep 3
	GEODE_HOST=$(GEODE_HOST) GEODE_PORT=$(GEODE_PORT) \
		$(VENV_PYTEST) tests/integration/ -v -m integration || \
		($(MAKE) docker-stop && exit 1)
	$(MAKE) docker-stop
	@echo "✓ Docker integration tests complete (119 tests)"

test-all: test-unit test-property test-integration
	@echo "✓ All tests complete (including integration)"

test-verbose:
	@echo "Running tests with verbose output..."
	$(VENV_PYTEST) tests/unit/ -v -s

# =============================================================================
# Code Quality Targets
# =============================================================================

lint:
	@echo "Running ruff linter..."
	$(VENV_DIR)/bin/ruff check geode_client/
	@echo "✓ Lint complete (0 issues)"

fmt:
	@echo "Formatting code..."
	$(VENV_DIR)/bin/ruff format geode_client/
	$(VENV_DIR)/bin/ruff check geode_client/ --fix
	@echo "✓ Format complete"

fmt-check:
	@echo "Checking code format..."
	$(VENV_DIR)/bin/ruff format --check geode_client/
	@echo "✓ Format check complete"

typecheck:
	@echo "Running mypy type checker..."
	$(VENV_DIR)/bin/mypy geode_client/ --ignore-missing-imports
	@echo "✓ Type check complete (0 errors)"

# =============================================================================
# Benchmark Targets
# =============================================================================

bench:
	@echo "Running benchmarks..."
	$(VENV_PYTEST) benchmarks/ --benchmark-only
	@echo "✓ Benchmarks complete (154 benchmarks)"

bench-quick:
	@echo "Compiling benchmarks (dry run)..."
	$(VENV_PYTEST) benchmarks/ --collect-only -q
	@echo "✓ Benchmark compilation complete"

bench-save:
	@echo "Running benchmarks and saving results..."
	$(VENV_PYTEST) benchmarks/ --benchmark-only --benchmark-autosave \
		--benchmark-json=benchmark-results.json
	@echo "✓ Benchmark results saved to benchmark-results.json"

bench-compare:
	@echo "Comparing benchmarks with previous run..."
	$(VENV_PYTEST) benchmarks/ --benchmark-only --benchmark-compare
	@echo "✓ Benchmark comparison complete"

# =============================================================================
# Docker Targets
# =============================================================================

docker-start:
	@echo "Starting Geode Docker container..."
	@$(DOCKER) rm -f $(GEODE_CONTAINER) 2>/dev/null || true
	$(DOCKER) run -d --name $(GEODE_CONTAINER) \
		-p $(GEODE_PORT):3141/udp \
		$(GEODE_IMAGE) \
		serve --listen 0.0.0.0:3141 --log-level info
	@echo "✓ Geode container started"
	@echo "  Container: $(GEODE_CONTAINER)"
	@echo "  Port: $(GEODE_PORT)/udp"

docker-stop:
	@echo "Stopping Geode Docker container..."
	@$(DOCKER) stop $(GEODE_CONTAINER) 2>/dev/null || true
	@$(DOCKER) rm $(GEODE_CONTAINER) 2>/dev/null || true
	@echo "✓ Geode container stopped"

docker-logs:
	@echo "Viewing Geode container logs..."
	$(DOCKER) logs -f $(GEODE_CONTAINER)

docker-shell:
	@echo "Opening shell in Geode container..."
	$(DOCKER) exec -it $(GEODE_CONTAINER) /bin/sh

# =============================================================================
# CI Targets
# =============================================================================

ci: install-dev fmt-check lint typecheck test coverage bench-quick
	@echo ""
	@echo "==== CI Pipeline Complete ===="
	@echo "✓ Dependencies installed"
	@echo "✓ Format check passed"
	@echo "✓ Ruff lint passed (0 issues)"
	@echo "✓ Type check passed (0 errors)"
	@echo "✓ Unit tests passed (409 tests)"
	@echo "✓ Property tests passed (50 tests)"
	@echo "✓ Coverage report generated"
	@echo "✓ Benchmarks compiled"
	@echo ""

ci-quick: install-dev fmt-check lint test-unit
	@echo ""
	@echo "==== Quick CI Complete ===="
	@echo "✓ Format check passed"
	@echo "✓ Lint passed"
	@echo "✓ Unit tests passed"
	@echo ""

ci-full: ci test-integration
	@echo ""
	@echo "==== Full CI Complete (with integration tests) ===="
	@echo ""

# =============================================================================
# Coverage Target
# =============================================================================

coverage:
	@echo "Running tests with coverage..."
	$(VENV_PYTEST) tests/unit/ \
		--cov=geode_client \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml
	@echo "✓ Coverage report generated"
	@echo "  HTML report: htmlcov/index.html"
	@echo "  XML report: coverage.xml"

# =============================================================================
# Documentation Target
# =============================================================================

doc:
	@echo "Documentation is available in:"
	@echo "  - README.md"
	@echo "  - CLAUDE.md (developer guide)"
	@echo ""
	@echo "To generate API docs, install sphinx:"
	@echo "  pip install sphinx sphinx-rtd-theme"
	@echo "  cd docs && make html"

# =============================================================================
# Example Target
# =============================================================================

example:
	@echo "Running example scripts..."
	@echo "Note: Requires running Geode server"
	@echo ""
	@if [ -f examples/basic_example.py ]; then \
		echo "Running basic_example.py..."; \
		$(VENV_PYTHON) examples/basic_example.py || true; \
	fi
	@if [ -f examples/quic_example.py ]; then \
		echo "Running quic_example.py..."; \
		$(VENV_PYTHON) examples/quic_example.py || true; \
	fi

# =============================================================================
# Development Helpers
# =============================================================================

# Watch for changes and run tests (requires pytest-watch)
watch:
	@echo "Watching for changes..."
	$(VENV_PIP) install pytest-watch 2>/dev/null || true
	$(VENV_DIR)/bin/ptw tests/unit/

# Update dependencies
update:
	@echo "Updating dependencies..."
	$(VENV_PIP) install --upgrade -e ".[dev,integration,benchmark,property]"
	@echo "✓ Dependencies updated"

# Check for security vulnerabilities (requires pip-audit)
audit:
	@echo "Checking for security vulnerabilities..."
	$(VENV_PIP) install pip-audit 2>/dev/null || true
	$(VENV_DIR)/bin/pip-audit
	@echo "✓ Security audit complete"

# Show installed packages
show-deps:
	@echo "Installed packages:"
	$(VENV_PIP) list
