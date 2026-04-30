SELECT customer_id,
       payoil_code,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY create_time DESC) rn
FROM ffp_order_payoil
WHERE deleted = 0;
