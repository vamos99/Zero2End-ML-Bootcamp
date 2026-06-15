# Notebook Reproducibility

The notebooks are portfolio experiments and decision-support prototypes. They
are not stored as production evidence.

## Execution Order

Run commands from `olist-intelligence/`:

```bash
python -m src.ml.ingest
python scripts/apply_sql_views.py --replace
python scripts/validate_notebooks.py
```

Then open JupyterLab and run notebooks from `notebooks/`:

1. `1_general_eda_and_prep.ipynb`
2. `2_logistics_engine.ipynb`
3. `3_customer_sentinel.ipynb`
4. `4_growth_engine.ipynb`
5. `5_final_evaluation.ipynb`
6. `6_executive_pipeline.ipynb`

## Methodology Guardrails

- Source notebooks are committed without execution counts or stored outputs.
- Report model metrics only after rerunning the source notebook or benchmark.
- Churn features are calculated before a cutoff; labels come from the following
  90-day window.
- The churn/repeat-purchase workflow checks class balance before training. On
  the current Olist snapshot, extreme imbalance is a valid reason to skip the
  model artifact and prefer cohort-retention analysis.
- Logistics evaluation uses a later-order holdout. Historical seller features
  remain a documented prototype limitation.
- Segmentation preserves all customers, assigns relative profile labels, and
  treats campaign actions as experiment hypotheses.
- ROI, uplift, calibration, production readiness, and drift are not claimed
  without supporting evidence.

## Generated Artifacts

Notebooks may write local model files and generated SQLite tables. These remain
ignored by Git and should be regenerated locally. A notebook may intentionally
skip a model artifact when its evaluation-readiness gate fails.
