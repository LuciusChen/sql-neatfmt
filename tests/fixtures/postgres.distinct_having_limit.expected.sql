SELECT DISTINCT customer_id,
                oil_site_id
FROM order_payoil
WHERE deleted = FALSE
GROUP BY customer_id, oil_site_id
HAVING COUNT(*) > 1
ORDER BY customer_id DESC
LIMIT 10
OFFSET 20;
