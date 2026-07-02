PYTHON ?= python
PIP ?= $(PYTHON) -m pip
STREAMLIT ?= streamlit
UVICORN ?= uvicorn

.PHONY: help setup compile lint test notebooks schema-contract validate validate-data reconcile-ingest bi-export service-config ci demo-build api dashboard

help:
	@echo "Common Olist Intelligence commands:"
	@echo "  make setup           Install Python dependencies"
	@echo "  make test            Run the pytest suite"
	@echo "  make validate        Run no-data validation checks"
	@echo "  make validate-data   Validate local Kaggle CSV, DB, quality, and generated tables"
	@echo "  make reconcile-ingest Compare ingestion manifest with DB row counts"
	@echo "  make bi-export       Export local SQL marts as BI-ready CSV files"
	@echo "  make demo-build      Build deterministic local dashboard outputs"
	@echo "  make api             Start the local FastAPI app"
	@echo "  make dashboard       Start the local Streamlit dashboard"

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

compile:
	$(PYTHON) -m compileall -q scripts src tests

lint:
	$(PYTHON) -m compileall -q src scripts
	$(PYTHON) -m flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics

test:
	$(PYTHON) -m pytest -q

notebooks:
	$(PYTHON) scripts/validate_notebooks.py

schema-contract:
	$(PYTHON) -m pytest tests/test_data_contract.py -q

validate: compile notebooks schema-contract

validate-data:
	$(PYTHON) scripts/validate_olist_schema.py --target all

reconcile-ingest:
	$(PYTHON) scripts/reconcile_ingestion_manifest.py

bi-export:
	$(PYTHON) scripts/export_bi_marts.py --apply-views --replace-views

service-config:
	API_KEY=$${API_KEY:-ci-placeholder-key} KAGGLE_USERNAME=$${KAGGLE_USERNAME:-ci-placeholder-user} KAGGLE_KEY=$${KAGGLE_KEY:-ci-placeholder-key} docker compose config --quiet
	bash -n run_local.sh

ci: validate test service-config

demo-build:
	$(PYTHON) scripts/build_local_demo.py

api:
	$(UVICORN) src.app:app --host 127.0.0.1 --port 8000 --reload

dashboard:
	$(STREAMLIT) run src/dashboard.py
