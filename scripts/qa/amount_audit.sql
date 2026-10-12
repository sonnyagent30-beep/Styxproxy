
\pset pager off
\echo '=== A) Orders with amount_paid_ngn > 50000 (possible 100x inflation) ==='
SELECT order_id, plan_code, amount_paid_ngn, status, provider, created_at
FROM orders
WHERE amount_paid_ngn > 50000
ORDER BY created_at DESC
LIMIT 50;

\echo '=== B) Count of PAID/FULFILLED orders with inflated amount ==='
SELECT count(*) AS inflated_paid_orders FROM orders
WHERE amount_paid_ngn > 50000 AND status IN ('paid','fulfilled','active');

\echo '=== C) All PAID/FULFILLED orders with amounts, newest 25 ==='
SELECT order_id, plan_code, amount_paid_ngn, status, provider, created_at
FROM orders
WHERE status IN ('paid','fulfilled','active')
ORDER BY created_at DESC
LIMIT 25;

\echo '=== D) Total revenue recorded vs suspected-inflated ==='
SELECT sum(amount_paid_ngn) AS total_recorded_ngn, count(*) AS n FROM orders
WHERE status IN ('paid','fulfilled','active');
