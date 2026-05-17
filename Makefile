.PHONY: help install install-dev test test-cov lint type-check clean run batch-example format

help:
	@echo "Convert2MD - Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run all tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make lint             - Run flake8 linter"
	@echo "  make type-check       - Run mypy type checker"
	@echo "  make format           - Format code with black"
	@echo ""
	@echo "Examples:"
	@echo "  make run              - Convert sample.pdf"
	@echo "  make batch-example    - Batch convert test_samples/"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            - Remove build artifacts and caches"
	@echo "  make venv             - Create virtual environment"

venv:
	python3 -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-watch mypy black flake8

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	ptw tests/ -- -v

lint:
	flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__

type-check:
	mypy src/ --config-file=.mypy.ini

format:
	black src/ tests/ --line-length=100

format-check:
	black src/ tests/ --line-length=100 --check

run:
	python convert2md.py convert sample.pdf --verbose

batch-example:
	@mkdir -p test_outputs
	python convert2md.py batch test_samples/ --output test_outputs/ --verbose

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf test_outputs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name '*.mo' -delete

setup:
	@echo "Setting up development environment..."
	make venv
	@echo "Activating virtual environment..."
	@echo "Run: source venv/bin/activate"
	@echo "Then run: make install-dev"

check: lint type-check test
	@echo "All checks passed!"

install-pandoc:
	@echo "Installing Pandoc..."
	@if command -v brew &> /dev/null; then \
		brew install pandoc; \
	elif command -v apt-get &> /dev/null; then \
		sudo apt-get install pandoc; \
	else \
		echo "Please install Pandoc manually from https://pandoc.org/installing.html"; \
	fi

docs:
	@echo "Generate project documentation"
	@echo "README.md - Project overview and features"
	@echo "QUICKSTART.md - Getting started guide"
	@echo "TEST_CHECKLIST.md - Test scenarios"
	@echo "CONTRIBUTING.md - Contributing guidelines"
	@echo "CHANGELOG.md - Version history"

.DEFAULT_GOAL := help
