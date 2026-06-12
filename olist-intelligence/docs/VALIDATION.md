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
python scripts/validate_olist_schema.py --target csv
python -m src.ml.ingest
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
```
