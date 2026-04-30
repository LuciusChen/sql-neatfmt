SELECT customer_name,
       NVL(TO_CHAR(create_time, 'YYYY-MM-DD'), 'unknown') create_date
FROM order_payoil
WHERE create_time >= TO_DATE('2026-04-01', 'YYYY-MM-DD')
  AND deleted = 0
ORDER BY create_date;
