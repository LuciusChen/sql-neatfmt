SELECT customer_name,
       COALESCE(TO_CHAR(create_time, 'YYYY-MM-DD'), 'unknown') create_date
FROM order_payoil
WHERE create_time >= CAST('2026-04-01' AS DATE)
  AND deleted = FALSE
ORDER BY create_date;
