WITH
  active_customers AS (
    SELECT customer_id,
           customer_name
    FROM customer
    WHERE disabled = 0
  ),
  recent_orders AS (
    SELECT id,
           code,
           customer_id
    FROM order_payoil
    WHERE create_time >= TO_DATE('2026-04-01', 'YYYY-MM-DD')
  )
SELECT ro.code,
       ac.customer_name
FROM recent_orders ro
         LEFT JOIN active_customers ac ON ac.customer_id = ro.customer_id
WHERE ac.customer_name IS NOT NULL;
