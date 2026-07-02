# Metric Dictionary

This dictionary documents the SQL view metrics used by the dashboard and
portfolio walkthrough. The definitions are intentionally small enough to audit
against the Olist source tables.

## `executive_order_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `order_date` | `DATE(order_purchase_timestamp)` | `orders` |
| `orders` | Distinct orders purchased on the day | `orders.order_id` |
| `customers` | Distinct customers with an order on the day | `orders.customer_id` |
| `product_revenue` | Sum of item prices per order, aggregated by day | `order_items.price` |
| `freight_revenue` | Sum of freight values per order, aggregated by day | `order_items.freight_value` |
| `avg_review_score` | Mean review score for orders on the day | `order_reviews.review_score` |

## `delivery_quality`

| Metric | Definition | Source |
| --- | --- | --- |
| `actual_delivery_days` | Delivered date minus purchase date | `orders` date columns |
| `estimated_delivery_days` | Estimated delivery date minus purchase date | `orders` date columns |
| `is_late` | `1` when `DATE(delivered_customer_date)` is after `DATE(estimated_delivery_date)`, `0` when on time, `NULL` when date is missing | `orders` date columns |

## `seller_performance`

| Metric | Definition | Source |
| --- | --- | --- |
| `orders` | Distinct delivered orders handled by seller | `order_items`, `orders` |
| `revenue` | Sum of product item prices handled by seller | `order_items.price` |
| `avg_review_score` | Mean review score for seller orders | `order_reviews.review_score` |
| `late_delivery_rate` | Average `is_late` multiplied by 100 | `orders` date columns |

## `payment_mix_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `order_date` | `DATE(order_purchase_timestamp)` | `orders` |
| `payment_type` | Olist payment method category | `order_payments.payment_type` |
| `orders` | Distinct orders using the payment type on that day | `order_payments.order_id` |
| `payment_records` | Payment rows for the type on that day | `order_payments` |
| `payment_value` | Sum of payment values | `order_payments.payment_value` |
| `avg_installments` | Average installment count | `order_payments.payment_installments` |

This view intentionally avoids joining to `order_items`; payment mix is a
payment-grain mart and should not duplicate item-level revenue.

## `review_delivery_drivers`

| Metric | Definition | Source |
| --- | --- | --- |
| `review_score` | Rounded order-level review score bucket from 1 to 5 | `order_reviews.review_score` |
| `orders` | Distinct delivered orders in the score bucket | `orders`, `order_reviews` |
| `avg_delivery_days` | Average delivered date minus purchase date | `orders` date columns |
| `late_delivery_rate` | Average late flag multiplied by 100 | `orders` date columns |

This view first aggregates reviews to order grain, then groups by score bucket
so duplicate review rows do not create fractional score categories.

## `seller_sla_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `seller_id` | Seller identifier | `sellers.seller_id` |
| `orders` | Distinct delivered orders handled by the seller | `order_items`, `orders` |
| `items` | Item rows handled by the seller | `order_items` |
| `product_revenue` | Sum of seller item prices | `order_items.price` |
| `freight_revenue` | Sum of seller freight values | `order_items.freight_value` |
| `avg_review_score` | Average order-level review score | `order_reviews.review_score` |
| `avg_delivery_days` | Average delivered date minus purchase date | `orders` date columns |
| `late_delivery_rate` | Average seller-order late flag multiplied by 100 | `orders` date columns |

This view aggregates to seller-order grain before seller-level grouping, which
prevents multi-item orders from inflating order counts.

## `seller_risk_scorecard`

| Metric | Definition | Source |
| --- | --- | --- |
| `orders` | Distinct orders handled by the seller, including delivered and non-delivered statuses | `order_items`, `orders` |
| `delivered_orders` | Seller orders with `order_status = 'delivered'` | `orders.order_status` |
| `product_revenue` | Sum of seller item prices | `order_items.price` |
| `freight_revenue` | Sum of seller freight values | `order_items.freight_value` |
| `late_delivery_rate` | Average delivered-order late flag multiplied by 100 | `orders` date columns |
| `low_review_rate` | Share of seller orders with average review score less than or equal to 2, multiplied by 100 | `order_reviews.review_score` |
| `canceled_unavailable_rate` | Share of seller orders with `canceled` or `unavailable` status, multiplied by 100 | `orders.order_status` |
| `cross_state_rate` | Share of seller orders where seller state differs from customer state, multiplied by 100 | `sellers`, `customers` |
| `risk_score` | Weighted priority score from late delivery, low review, canceled/unavailable, cross-state and order-volume signals, capped at 100 | Derived |
| `risk_level` | `high`, `medium`, or `low` bucket from `risk_score` | Derived |

This scorecard is an operating-priority heuristic, not measured intervention
impact. It is designed to help decide which sellers deserve review first.

## `category_performance_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `category` | English product category when available, otherwise raw category or `Other` | `products`, `product_category_name_translation` |
| `orders` | Distinct delivered orders containing the category | `orders`, `order_items` |
| `items` | Item rows sold in the category | `order_items` |
| `product_revenue` | Sum of category item prices | `order_items.price` |
| `freight_revenue` | Sum of category item freight values | `order_items.freight_value` |
| `avg_review_score` | Average order-level review score for orders containing the category | `order_reviews.review_score` |
| `avg_delivery_days` | Average delivered date minus purchase date | `orders` date columns |
| `late_delivery_rate` | Average category-order late flag multiplied by 100 | `orders` date columns |

This view groups at category-order grain before category-level aggregation. The
grain keeps item revenue additive while reducing review and order-count
inflation from multi-item orders.

## `location_service_level_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `customer_state` | Customer delivery state | `customers.customer_state` |
| `seller_state` | Seller origin state | `sellers.seller_state` |
| `lane_type` | `same_state` when customer and seller states match, otherwise `cross_state` | Derived |
| `orders` | Distinct delivered orders in the customer-state/seller-state lane | `orders`, `order_items` |
| `sellers` | Distinct sellers serving the lane | `order_items.seller_id` |
| `items` | Item rows in the lane | `order_items` |
| `product_revenue` | Sum of lane item prices | `order_items.price` |
| `freight_revenue` | Sum of lane freight values | `order_items.freight_value` |
| `avg_review_score` | Average order-level review score in the lane | `order_reviews.review_score` |
| `avg_delivery_days` | Average delivered date minus purchase date | `orders` date columns |
| `late_delivery_rate` | Average lane late flag multiplied by 100 | `orders` date columns |
| `customer_geo_coverage_pct` | Share of seller-order rows with customer ZIP coordinates | `geolocation` |
| `seller_geo_coverage_pct` | Share of seller-order rows with seller ZIP coordinates | `geolocation` |

This view aggregates geolocation to ZIP prefix before joining. It intentionally
starts with state-lane service levels and coordinate coverage instead of a
decorative map or database-specific distance formula.

## `customer_segment_summary`

| Metric | Definition | Source |
| --- | --- | --- |
| `segment_id` | Cluster id generated by the segmentation workflow | `customer_segments.Cluster` |
| `customers` | Customers in the cluster | `customer_segments` |
| `avg_recency` | Mean recency value in the cluster | `customer_segments.Recency` |
| `avg_frequency` | Mean frequency value in the cluster | `customer_segments.Frequency` |
| `avg_monetary` | Mean monetary value in the cluster | `customer_segments.Monetary` |

## `customer_cohort_retention`

| Metric | Definition | Source |
| --- | --- | --- |
| `cohort_month` | Month of the customer's first non-canceled Olist order | `orders`, `customers` |
| `months_since_first_order` | Month offset between activity month and cohort month | `orders.order_purchase_timestamp` |
| `cohort_customers` | Customers whose first qualifying order happened in the cohort month | `customers.customer_unique_id` |
| `active_customers` | Cohort customers with a qualifying order in the offset month | `customers.customer_unique_id` |
| `orders` | Qualifying orders placed by active cohort customers in the offset month | `orders.order_id` |
| `retention_rate` | `active_customers / cohort_customers * 100` | Derived |

This view uses `customer_unique_id` instead of `customer_id` because Olist can
assign a different `customer_id` to separate orders from the same underlying
customer. Orders with `canceled` or `unavailable` status are excluded from the
cohort and repeat-purchase calculation.

## Reconciliation

`tests/test_sql_views.py` builds a small SQLite fixture, applies every SQL view
with `scripts/apply_sql_views.py`, and checks expected revenue, review,
late-delivery, payment mix, seller SLA, category performance, location service
levels, seller risk scoring, customer cohort retention and segment aggregates.
This keeps the SQL layer testable without requiring the full Kaggle dataset.

`tests/test_data_contract.py` validates the expected Kaggle source contract:
9 CSV files, 52 source columns, the repository's CSV-to-table naming convention,
and a SQLite smoke check for the ingested table schema. It also covers stable
data-quality rules for empty tables, duplicate keys, orphan joins, accepted
status/payment values, review-score range, negative amounts and delivery dates
that occur before purchase dates.
