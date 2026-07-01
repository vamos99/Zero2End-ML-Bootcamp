CREATE VIEW IF NOT EXISTS location_service_level_summary AS
WITH geo_by_zip AS (
    SELECT
        geolocation_zip_code_prefix AS zip_code_prefix,
        AVG(geolocation_lat) AS latitude,
        AVG(geolocation_lng) AS longitude
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
),
review_by_order AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score
    FROM order_reviews
    GROUP BY order_id
),
seller_order AS (
    SELECT
        order_id,
        seller_id,
        COUNT(*) AS items,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue
    FROM order_items
    GROUP BY order_id, seller_id
),
location_order AS (
    SELECT
        COALESCE(c.customer_state, 'Unknown') AS customer_state,
        COALESCE(s.seller_state, 'Unknown') AS seller_state,
        CASE
            WHEN c.customer_state = s.seller_state THEN 'same_state'
            ELSE 'cross_state'
        END AS lane_type,
        so.order_id,
        so.seller_id,
        so.items,
        so.product_revenue,
        so.freight_revenue,
        r.avg_review_score,
        CASE WHEN cg.latitude IS NOT NULL AND cg.longitude IS NOT NULL THEN 1.0 ELSE 0.0 END
            AS customer_geo_available,
        CASE WHEN sg.latitude IS NOT NULL AND sg.longitude IS NOT NULL THEN 1.0 ELSE 0.0 END
            AS seller_geo_available,
        JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)
            AS actual_delivery_days,
        CASE
            WHEN o.order_delivered_customer_date IS NULL
              OR o.order_estimated_delivery_date IS NULL
            THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date)
            THEN 1.0
            ELSE 0.0
        END AS late_flag
    FROM seller_order so
    JOIN orders o ON so.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN sellers s ON so.seller_id = s.seller_id
    LEFT JOIN geo_by_zip cg ON c.customer_zip_code_prefix = cg.zip_code_prefix
    LEFT JOIN geo_by_zip sg ON s.seller_zip_code_prefix = sg.zip_code_prefix
    LEFT JOIN review_by_order r ON so.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
)
SELECT
    customer_state,
    seller_state,
    lane_type,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT seller_id) AS sellers,
    SUM(items) AS items,
    SUM(product_revenue) AS product_revenue,
    SUM(freight_revenue) AS freight_revenue,
    AVG(avg_review_score) AS avg_review_score,
    AVG(actual_delivery_days) AS avg_delivery_days,
    AVG(late_flag) * 100.0 AS late_delivery_rate,
    AVG(customer_geo_available) * 100.0 AS customer_geo_coverage_pct,
    AVG(seller_geo_available) * 100.0 AS seller_geo_coverage_pct
FROM location_order
GROUP BY customer_state, seller_state, lane_type;
