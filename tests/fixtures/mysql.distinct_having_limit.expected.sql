SELECT DISTINCT customer_id,
                oil_site_id
FROM ffp_order_payoil
WHERE deleted = 0
GROUP BY customer_id, oil_site_id
HAVING COUNT(1) > 1
ORDER BY customer_id DESC
LIMIT 10
OFFSET 20;
