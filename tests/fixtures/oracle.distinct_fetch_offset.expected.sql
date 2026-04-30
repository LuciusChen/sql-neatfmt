SELECT DISTINCT customer_id,
                oil_site_id
FROM order_payoil
WHERE deleted = 0
ORDER BY customer_id
FETCH NEXT 10 ROWS ONLY
OFFSET 5 ROWS;
