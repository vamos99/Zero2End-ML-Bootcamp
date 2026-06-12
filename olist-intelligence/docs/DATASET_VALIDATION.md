# Dataset Validation Note

This note records the local validation result for the uploaded Olist archive used during the audit. Raw CSV files are not committed to the repository.

## Source

- Dataset family: Brazilian E-Commerce Public Dataset by Olist
- Expected contract source: `src/data_contract.py`
- Expected CSV files: 9
- Expected raw columns: 52

## Local archive check

The uploaded archive was checked against the repository schema contract.

| Check | Result |
| --- | --- |
| Expected CSV files present | Pass |
| Extra CSV files | None observed |
| Missing CSV files | None observed |
| Header names | Pass |
| Header order | Pass |
| Raw data committed | No |

## Expected files

- `olist_customers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `product_category_name_translation.csv`

## Operational note

Run the repository validation commands after copying the CSV files to `data/raw/`:

```bash
python scripts/validate_olist_schema.py --target csv
python -m src.ml.ingest
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
```

The archive check confirms that the file-level schema matches the expected Kaggle contract. It does not replace database-level quality checks after ingestion.
