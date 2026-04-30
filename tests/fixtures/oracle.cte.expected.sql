WITH
  recent_order AS (
    SELECT id,
           code,
           customer_id
    FROM order_payoil
    WHERE create_time >= TO_DATE('2026-04-01', 'YYYY-MM-DD')
      AND deleted = 0
  )
SELECT ro.code,
       c.customer_name
FROM recent_order ro
         LEFT JOIN customer c ON c.customer_id = ro.customer_id
WHERE c.customer_name IS NOT NULL
ORDER BY ro.id DESC;
