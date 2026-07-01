CREATE VIEW IF NOT EXISTS category_performance_summary AS
WITH review_by_order AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score
    FROM order_reviews
    GROUP BY order_id
),
category_order AS (
    SELECT
        COALESCE(
            t.product_category_name_english,
            p.product_category_name,
            'Other'
        ) AS category,
        o.order_id,
        COUNT(*) AS items,
        SUM(oi.price) AS product_revenue,
        SUM(oi.freight_value) AS freight_revenue,
        AVG(r.avg_review_score) AS avg_review_score,
        AVG(
            JULIANDAY(o.order_delivered_customer_date)
            - JULIANDAY(o.order_purchase_timestamp)
        ) AS avg_delivery_days,
        AVG(
            CASE
                WHEN o.order_delivered_customer_date IS NULL
                  OR o.order_estimated_delivery_date IS NULL
                THEN NULL
                WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date)
                THEN 1.0
                ELSE 0.0
            END
        ) AS late_flag
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    LEFT JOIN review_by_order r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY
        COALESCE(
            t.product_category_name_english,
            p.product_category_name,
            'Other'
        ),
        o.order_id
)
SELECT
    category,
    COUNT(DISTINCT order_id) AS orders,
    SUM(items) AS items,
    SUM(product_revenue) AS product_revenue,
    SUM(freight_revenue) AS freight_revenue,
    AVG(avg_review_score) AS avg_review_score,
    AVG(avg_delivery_days) AS avg_delivery_days,
    AVG(late_flag) * 100.0 AS late_delivery_rate
FROM category_order
GROUP BY category;
