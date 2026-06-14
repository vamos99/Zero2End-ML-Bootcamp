# Olist Dataset

## Source

This project uses the public
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
Raw data is downloaded and processed locally. It is not committed to Git.

Recommended local folder:

```text
olist-intelligence/data/raw/
```

The legacy local folder `olist-intelligence/olist-dataset/` is also recognized
by existing development workflows, but new setup instructions should prefer
`data/raw/`.

## Expected Files

The executable source contract is defined in `src/data_contract.py`.

| CSV file | Main purpose |
| --- | --- |
| `olist_customers_dataset.csv` | Customer identity and location |
| `olist_geolocation_dataset.csv` | ZIP-prefix coordinate observations |
| `olist_order_items_dataset.csv` | Product, seller, price, and freight line items |
| `olist_order_payments_dataset.csv` | Payment methods, installments, and values |
| `olist_order_reviews_dataset.csv` | Review scores and Portuguese review text |
| `olist_orders_dataset.csv` | Order status and lifecycle timestamps |
| `olist_products_dataset.csv` | Product category and physical attributes |
| `olist_sellers_dataset.csv` | Seller identity and location |
| `product_category_name_translation.csv` | Portuguese-to-English category mapping |

The current contract expects 9 CSV files and 52 required source columns.
Source misspellings such as `product_name_lenght` and
`product_description_lenght` are intentionally preserved in the raw layer.

## Local Data Policy

- Do not commit raw CSVs, Kaggle archives, `olist.db`, generated model files,
  notebook outputs containing data, credentials, or `.env`.
- Keep source data under an ignored local folder.
- Keep only schema contracts, transformations, tests, and documentation in Git.
- Treat generated `logistics_predictions` and `customer_segments` as local
  workflow outputs, not raw Olist tables.

## Validation

From `olist-intelligence/`:

```bash
python scripts/validate_olist_schema.py --target csv
python -m src.ml.ingest
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
python scripts/apply_sql_views.py --replace
```

Validation should fail clearly when required local data or the database is
missing. A successful raw-schema check does not prove generated prediction or
segment tables exist.

## Known Limitations

- The dataset covers a historical marketplace period, not a live business.
- Orders, items, payments, and reviews have different grains. One-to-many
  tables must be aggregated before order-level metrics are joined.
- `customer_id` is an order/customer record identifier;
  `customer_unique_id` is safer for repeat-customer and retention analysis.
- Review comments are Portuguese and are frequently missing.
- Geolocation contains many observations per ZIP prefix and should be
  aggregated before joining.
- Current model outputs are portfolio prototypes and require leakage-aware,
  time-based validation before operational claims.

## Future Analytics Candidates

Review-text analysis and geolocation analysis are valid future phases because
the source files contain review title/message fields and customer, seller, and
ZIP-prefix location fields. They are not marked as implemented.
