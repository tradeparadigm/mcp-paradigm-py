# mcp-paradigm-py — common dev tasks
# https://just.systems

PYTHON := env_var_or_default("PYTHON", ".venv/bin/python")

# Show available recipes
default:
    @just --list

# Install dev dependencies and pre-commit hooks
install-dev:
    pip install -e ".[dev]"
    pre-commit install

# Format with ruff
format:
    {{PYTHON}} -m ruff format src tests

# Check formatting (CI)
format-check:
    {{PYTHON}} -m ruff format --check src tests

# Lint with ruff (autofix)
lint:
    {{PYTHON}} -m ruff check src tests --fix

# Lint without autofix (CI)
lint-check:
    {{PYTHON}} -m ruff check src tests

# Run unit tests
test:
    {{PYTHON}} -m pytest

# Run tests with HTML coverage report
test-cov:
    {{PYTHON}} -m pytest --cov=mcp_paradigm --cov-report=html

# Format + lint + test
check: format lint test

# Run pre-commit across the tree
pre-commit:
    pre-commit run --all-files

# Build sdist + wheel
build:
    uv build

# Publish to PyPI (requires trusted publishing or PYPI_TOKEN)
publish: build
    uv publish

# Build MCPB bundle (.mcpb)
mcpb:
    npx --yes @anthropic-ai/mcpb pack .

# Build docker image
docker:
    docker build -t mcp-paradigm-py:dev .

# Run the server (stdio)
run:
    {{PYTHON}} -m mcp_paradigm

# Clean caches + build artifacts
clean:
    find . -type d \( -name "__pycache__" -o -name "*.egg-info" -o -name ".ruff_cache" -o -name ".pytest_cache" \) -prune -exec rm -rf {} +
    rm -rf dist build htmlcov .coverage coverage.xml *.mcpb
    find . -type f -name "*.pyc" -delete
