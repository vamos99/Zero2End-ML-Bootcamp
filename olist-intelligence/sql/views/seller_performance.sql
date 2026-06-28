CREATE VIEW IF NOT EXISTS seller_performance AS
WITH seller_orders AS (
    SELECT
        s.seller_id,
        s.seller_state,
        oi.order_id,
        oi.price,
        r.review_score,
        CASE
            WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_estimated_delivery_date IS NULL THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1.0
            ELSE 0.0
        END AS is_late
    FROM sellers s
    JOIN order_items oi ON s.seller_id = oi.seller_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
)
SELECT
    seller_id,
    seller_state,
    COUNT(DISTINCT order_id) AS orders,
    SUM(price) AS revenue,
    AVG(review_score) AS avg_review_score,
    AVG(is_late) * 100 AS late_delivery_rate
FROM seller_orders
GROUP BY seller_id, seller_state;
