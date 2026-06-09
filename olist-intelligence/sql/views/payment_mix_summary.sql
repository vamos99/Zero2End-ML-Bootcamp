CREATE VIEW IF NOT EXISTS payment_mix_summary AS
SELECT
    DATE(o.order_purchase_timestamp) AS order_date,
    op.payment_type,
    COUNT(DISTINCT op.order_id) AS orders,
    COUNT(*) AS payment_records,
    SUM(op.payment_value) AS payment_value,
    AVG(op.payment_installments) AS avg_installments
FROM order_payments op
JOIN orders o ON op.order_id = o.order_id
GROUP BY DATE(o.order_purchase_timestamp), op.payment_type;
