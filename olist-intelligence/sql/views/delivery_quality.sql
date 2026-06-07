CREATE VIEW IF NOT EXISTS delivery_quality AS
SELECT
    o.order_id,
    DATE(o.order_purchase_timestamp) AS order_date,
    c.customer_state,
    r.review_score,
    CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS actual_delivery_days,
    CAST(JULIANDAY(o.order_estimated_delivery_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS estimated_delivery_days,
    CASE
        WHEN o.order_delivered_customer_date IS NULL THEN NULL
        WHEN o.order_estimated_delivery_date IS NULL THEN NULL
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1
        ELSE 0
    END AS is_late
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered';
