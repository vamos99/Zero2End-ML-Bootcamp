CREATE VIEW IF NOT EXISTS executive_order_summary AS
WITH order_value AS (
    SELECT
        order_id,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue
    FROM order_items
    GROUP BY order_id
)
SELECT
    DATE(o.order_purchase_timestamp) AS order_date,
    COUNT(DISTINCT o.order_id) AS orders,
    COUNT(DISTINCT o.customer_id) AS customers,
    SUM(COALESCE(ov.product_revenue, 0)) AS product_revenue,
    SUM(COALESCE(ov.freight_revenue, 0)) AS freight_revenue,
    AVG(r.review_score) AS avg_review_score
FROM orders o
LEFT JOIN order_value ov ON o.order_id = ov.order_id
LEFT JOIN order_reviews r ON o.order_id = r.order_id
GROUP BY DATE(o.order_purchase_timestamp);
