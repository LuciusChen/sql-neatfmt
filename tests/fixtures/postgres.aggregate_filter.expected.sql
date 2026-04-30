SELECT customer_id,
       COUNT(*) FILTER(WHERE deleted = FALSE) active_count
FROM order_payoil
GROUP BY customer_id
HAVING COUNT(*) > 1;
