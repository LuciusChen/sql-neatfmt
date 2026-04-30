SELECT customer_id,
       code,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY create_time DESC) rn
FROM order_payoil
WHERE deleted = FALSE;
