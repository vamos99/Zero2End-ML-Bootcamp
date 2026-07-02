# Validation

Local archive check result:

- Expected CSV count: 9
- Expected column count: 52
- Missing files: none
- Extra files: none
- Header names: pass
- Header order: pass

Follow-up commands:

```bash
make test
make validate
```

`make validate` raw CSV veya `olist.db` gerektirmeyen no-data kontrollerini
çalıştırır: Python compile, notebook source validation ve schema-contract unit
testleri.

Local Kaggle CSV dosyaları ve `olist.db` hazırlandıktan sonra veri kontrolleri:

```bash
python scripts/validate_olist_schema.py --target csv
python -m src.ml.ingest
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
python scripts/build_local_demo.py
python scripts/validate_olist_schema.py --target generated
make validate-data
make reconcile-ingest
```

`--target generated` validates `logistics_predictions` and
`customer_segments`. The local demo builder fails when raw database quality or
generated-output contracts fail.

`make reconcile-ingest` compares `data/processed/ingestion_manifest.json`
against the current database row counts. The manifest is created by
`python -m src.ml.ingest` and stays local because `data/` is Git-ignored.

The CLI prints the selected check group in the success line. This matters
because raw CSV validation, database schema validation, generated table
validation, and full data-quality checks prove different things.

Runtime API readiness is a separate check:

```bash
curl http://127.0.0.1:8000/ready
```

`generated_tables` confirms local dashboard outputs exist. `loaded_models`
confirms model artefacts were loaded for live API endpoints. A ready database
does not imply that churn, delivery, or recommender models are loaded.
