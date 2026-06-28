CREATE VIEW IF NOT EXISTS seller_sla_summary AS
WITH seller_order_items AS (
    SELECT
        seller_id,
        order_id,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue,
        COUNT(*) AS items
    FROM order_items
    GROUP BY seller_id, order_id
),
review_by_order AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM order_reviews
    GROUP BY order_id
),
seller_orders AS (
    SELECT
        s.seller_id,
        s.seller_state,
        soi.order_id,
        soi.product_revenue,
        soi.freight_revenue,
        soi.items,
        r.review_score,
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS actual_delivery_days,
        CASE
            WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_estimated_delivery_date IS NULL THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1.0
            ELSE 0.0
        END AS is_late
    FROM seller_order_items soi
    JOIN sellers s ON soi.seller_id = s.seller_id
    JOIN orders o ON soi.order_id = o.order_id
    LEFT JOIN review_by_order r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
)
SELECT
    seller_id,
    seller_state,
    COUNT(DISTINCT order_id) AS orders,
    SUM(items) AS items,
    SUM(product_revenue) AS product_revenue,
    SUM(freight_revenue) AS freight_revenue,
    AVG(review_score) AS avg_review_score,
    AVG(actual_delivery_days) AS avg_delivery_days,
    AVG(is_late) * 100 AS late_delivery_rate
FROM seller_orders
GROUP BY seller_id, seller_state;
