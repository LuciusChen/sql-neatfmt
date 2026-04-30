WITH
  active_customers AS (
    SELECT customer_id,
           customer_name
    FROM customer
    WHERE disabled = FALSE
  ),
  recent_orders AS (
    SELECT id,
           code,
           customer_id
    FROM order_payoil
    WHERE create_time >= CAST('2026-04-01' AS DATE)
  )
SELECT ro.code,
       ac.customer_name
FROM recent_orders ro
         LEFT JOIN active_customers ac ON ac.customer_id = ro.customer_id
WHERE ac.customer_name IS NOT NULL;
