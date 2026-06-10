CREATE VIEW IF NOT EXISTS customer_cohort_retention AS
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        DATE(o.order_purchase_timestamp) AS order_date,
        DATE(STRFTIME('%Y-%m-01', o.order_purchase_timestamp)) AS order_month
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE c.customer_unique_id IS NOT NULL
        AND o.order_purchase_timestamp IS NOT NULL
        AND o.order_status NOT IN ('canceled', 'unavailable')
),
first_orders AS (
    SELECT
        customer_unique_id,
        MIN(order_date) AS first_order_date,
        DATE(STRFTIME('%Y-%m-01', MIN(order_date))) AS cohort_month
    FROM customer_orders
    GROUP BY customer_unique_id
),
cohort_activity AS (
    SELECT
        f.cohort_month,
        (
            (CAST(STRFTIME('%Y', co.order_month) AS INTEGER) - CAST(STRFTIME('%Y', f.cohort_month) AS INTEGER)) * 12
            + (CAST(STRFTIME('%m', co.order_month) AS INTEGER) - CAST(STRFTIME('%m', f.cohort_month) AS INTEGER))
        ) AS months_since_first_order,
        COUNT(DISTINCT co.customer_unique_id) AS active_customers,
        COUNT(DISTINCT co.order_id) AS orders
    FROM customer_orders co
    JOIN first_orders f ON co.customer_unique_id = f.customer_unique_id
    GROUP BY f.cohort_month, months_since_first_order
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_unique_id) AS cohort_customers
    FROM first_orders
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    ca.months_since_first_order,
    cs.cohort_customers,
    ca.active_customers,
    ca.orders,
    ca.active_customers * 100.0 / cs.cohort_customers AS retention_rate
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
ORDER BY ca.cohort_month, ca.months_since_first_order;
