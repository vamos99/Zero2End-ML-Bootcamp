# Model Cards

These cards describe portfolio prototypes and local demo outputs. They do not
claim production readiness, measured business uplift, or live monitoring.
Current measured values are summarized in [`RESULTS.md`](RESULTS.md).

## Delivery Duration Model

**Decision supported:** identify orders that may need operational review.

**Target:** elapsed days from purchase to delivered-customer timestamp.

**Evaluation:** later-order temporal holdout. Report RMSE only after rerunning
the benchmark or notebook on the current local dataset.

**Leakage guardrail:** seller average rating uses only seller-order reviews
available before the current seller order. Current and future reviews are
excluded through a shifted SQL window.

**Known limitations:** the local demo builder uses Olist's estimated delivery
date as a deterministic baseline, not the trained ML model. The dashboard
labels this output as a long-delivery estimate rather than a production risk
score.

## Repeat-Purchase Risk Candidate

**Decision supported:** determine whether the dataset can support a predictive
repeat-purchase experiment.

**Label:** no delivered purchase in the 90 days after a feature cutoff.

**Evaluation gate:** training is skipped when either class has fewer than 20
rows or less than 5% share. The current local snapshot is not presented as a
decision-ready churn model when this gate fails.

**Known limitations:** Olist has a short and sparse repeat-purchase history.
Cohort retention remains the preferred source-backed customer behavior view.

## Product Recommender Prototype

**Decision supported:** explore personalized product ranking and cold-start
fallback behavior.

**Method:** sparse user-product interactions with Truncated SVD.

**Evaluation:** deterministic leave-one-out evaluation on repeat users whose
held-out product remains in the training catalog. Training reports hit rate at
K, catalog coverage at K, and eligible user count.

**Inference guardrail:** products already purchased by a known customer are
excluded when the artifact contains interaction history. Unknown customers
receive popular product-category labels, explicitly marked as category output.

**Known limitations:** eligible repeat-user coverage can be small; novelty,
ranking calibration, and cold-start quality remain unmeasured.

## Customer Segmentation

**Decision supported:** create relative RFM profiles for exploratory targeting.

**Method:** 1st-99th percentile clipping, standard scaling, deterministic
K-Means with four clusters, then relative profile names based on recency,
frequency, and monetary ranking.

**Known limitations:** cluster IDs have no stable business meaning. Consumers
must use the generated `Segment` label. Stability, drift, and campaign uplift
are not business-validated. The local demo build reports seed-stability ARI and
a sampled silhouette score for technical diagnostics.
