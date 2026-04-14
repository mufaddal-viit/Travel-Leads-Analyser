.PHONY: install run test clean dashboard-config

## install: Install all Python dependencies from requirements.txt
install:
	pip install -r requirements.txt

## run: Run the pipeline against the sample CSV file
run:
	python -m src.main --input sample_leads.csv

## run-debug: Run with verbose debug logging
run-debug:
	python -m src.main --input sample_leads.csv --log-level DEBUG

## test: Run the test suite with verbose output
test:
	python -m pytest tests/ -v

## dashboard-config: Generate Dashboard/config.js from .env
dashboard-config:
	python generate_dashboard_config.py

## clean: Remove compiled Python files and cache directories
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
