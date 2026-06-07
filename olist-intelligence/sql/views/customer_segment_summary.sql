CREATE VIEW IF NOT EXISTS customer_segment_summary AS
SELECT
    "Cluster" AS segment_id,
    COUNT(*) AS customers,
    AVG("Recency") AS avg_recency,
    AVG("Frequency") AS avg_frequency,
    AVG("Monetary") AS avg_monetary
FROM customer_segments
GROUP BY "Cluster";
