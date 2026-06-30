EMPTY_TOTALS = {
    "total_revenue": 0.0,
    "avg_order_value": 0.0,
    "unique_customers": 0,
    "revenue_per_customer": 0.0,
}

EMPTY_REVIEW_DELIVERY = {
    "avg_review_score": 0.0,
    "late_delivery_rate": 0.0,
    "review_count": 0,
}

EMPTY_SOURCE_BASELINES = {
    "delivery": {
        "delivered_orders": 0,
        "late_orders": 0,
        "late_delivery_rate_pct": 0.0,
        "avg_days_late_when_late": 0.0,
    },
    "repeat_purchase": {
        "unique_customers": 0,
        "repeat_customers": 0,
        "one_time_customers": 0,
        "repeat_customer_rate_pct": 0.0,
        "one_time_customer_rate_pct": 0.0,
    },
}
