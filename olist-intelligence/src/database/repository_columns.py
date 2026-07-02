PAYMENT_MIX_COLUMNS = [
    "payment_type",
    "orders",
    "payment_records",
    "payment_value",
    "avg_installments",
]

REVENUE_BY_STATE_COLUMNS = ["customer_state", "order_count", "revenue"]

REVIEW_DELIVERY_MATRIX_COLUMNS = [
    "review_score",
    "order_count",
    "late_delivery_rate",
]

COHORT_RETENTION_COLUMNS = [
    "cohort_month",
    "months_since_first_order",
    "cohort_customers",
    "active_customers",
    "retention_rate",
]

SELLER_SLA_COLUMNS = [
    "seller_id",
    "seller_state",
    "orders",
    "product_revenue",
    "avg_review_score",
    "avg_delivery_days",
    "late_delivery_rate",
]

SELLER_RISK_SCORECARD_COLUMNS = [
    "seller_id",
    "seller_state",
    "orders",
    "delivered_orders",
    "items",
    "product_revenue",
    "freight_revenue",
    "avg_review_score",
    "late_delivery_rate",
    "low_review_rate",
    "canceled_unavailable_rate",
    "cross_state_rate",
    "risk_score",
    "risk_level",
]

CATEGORY_PERFORMANCE_MART_COLUMNS = [
    "category",
    "orders",
    "items",
    "product_revenue",
    "freight_revenue",
    "avg_review_score",
    "avg_delivery_days",
    "late_delivery_rate",
]

LOCATION_SERVICE_LEVEL_COLUMNS = [
    "customer_state",
    "seller_state",
    "lane_type",
    "orders",
    "sellers",
    "items",
    "product_revenue",
    "freight_revenue",
    "avg_review_score",
    "avg_delivery_days",
    "late_delivery_rate",
    "customer_geo_coverage_pct",
    "seller_geo_coverage_pct",
]

LOGISTICS_DETAILS_COLUMNS = [
    "customer_id",
    "Tahmini Süre (Gün)",
    "Gerçekleşen (Gün)",
    "order_purchase_timestamp",
]

TARGET_AUDIENCE_COLUMNS = [
    "customer_unique_id",
    "Recency",
    "Frequency",
    "Monetary",
    "Cluster",
    "Segment",
]
