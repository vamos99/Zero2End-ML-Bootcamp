CREATE VIEW IF NOT EXISTS seller_risk_scorecard AS
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
        c.customer_state,
        soi.order_id,
        o.order_status,
        soi.product_revenue,
        soi.freight_revenue,
        soi.items,
        r.review_score,
        CASE
            WHEN o.order_status != 'delivered' THEN NULL
            WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_estimated_delivery_date IS NULL THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1.0
            ELSE 0.0
        END AS is_late,
        CASE
            WHEN r.review_score IS NOT NULL AND r.review_score <= 2 THEN 1.0
            ELSE 0.0
        END AS is_low_review,
        CASE
            WHEN o.order_status IN ('canceled', 'unavailable') THEN 1.0
            ELSE 0.0
        END AS is_canceled_or_unavailable,
        CASE
            WHEN c.customer_state IS NOT NULL
                 AND s.seller_state IS NOT NULL
                 AND c.customer_state != s.seller_state THEN 1.0
            ELSE 0.0
        END AS is_cross_state
    FROM seller_order_items soi
    JOIN sellers s ON soi.seller_id = s.seller_id
    JOIN orders o ON soi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN review_by_order r ON o.order_id = r.order_id
),
seller_metrics AS (
    SELECT
        seller_id,
        seller_state,
        COUNT(DISTINCT order_id) AS orders,
        SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
        SUM(items) AS items,
        SUM(product_revenue) AS product_revenue,
        SUM(freight_revenue) AS freight_revenue,
        AVG(review_score) AS avg_review_score,
        AVG(is_late) * 100 AS late_delivery_rate,
        AVG(is_low_review) * 100 AS low_review_rate,
        AVG(is_canceled_or_unavailable) * 100 AS canceled_unavailable_rate,
        AVG(is_cross_state) * 100 AS cross_state_rate
    FROM seller_orders
    GROUP BY seller_id, seller_state
),
seller_scores AS (
    SELECT
        *,
        (
            COALESCE(late_delivery_rate, 0) * 0.35
            + COALESCE(low_review_rate, 0) * 0.25
            + COALESCE(canceled_unavailable_rate, 0) * 0.20
            + COALESCE(cross_state_rate, 0) * 0.10
            + CASE
                WHEN orders >= 100 THEN 10
                WHEN orders >= 50 THEN 6
                WHEN orders >= 20 THEN 3
                ELSE 0
              END
        ) AS raw_risk_score
    FROM seller_metrics
)
SELECT
    seller_id,
    seller_state,
    orders,
    delivered_orders,
    items,
    product_revenue,
    freight_revenue,
    avg_review_score,
    late_delivery_rate,
    low_review_rate,
    canceled_unavailable_rate,
    cross_state_rate,
    ROUND(CASE WHEN raw_risk_score > 100 THEN 100 ELSE raw_risk_score END, 2) AS risk_score,
    CASE
        WHEN raw_risk_score >= 60 THEN 'high'
        WHEN raw_risk_score >= 35 THEN 'medium'
        ELSE 'low'
    END AS risk_level
FROM seller_scores;
