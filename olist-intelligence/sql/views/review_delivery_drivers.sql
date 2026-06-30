CREATE VIEW IF NOT EXISTS review_delivery_drivers AS
WITH review_by_order AS (
    SELECT
        order_id,
        CAST(ROUND(AVG(review_score), 0) AS INTEGER) AS review_score
    FROM order_reviews
    GROUP BY order_id
),
delivered_orders AS (
    SELECT
        o.order_id,
        r.review_score,
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS actual_delivery_days,
        CASE
            WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_estimated_delivery_date IS NULL THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1.0
            ELSE 0.0
        END AS is_late
    FROM orders o
    JOIN review_by_order r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
)
SELECT
    review_score,
    COUNT(DISTINCT order_id) AS orders,
    AVG(actual_delivery_days) AS avg_delivery_days,
    AVG(is_late) * 100 AS late_delivery_rate
FROM delivered_orders
WHERE review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;
