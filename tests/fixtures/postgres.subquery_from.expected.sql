SELECT x.customer_id,
       x.order_count
FROM (SELECT customer_id, COUNT(*) AS order_count FROM order_payoil WHERE deleted = FALSE GROUP BY customer_id) x
WHERE x.order_count > 1
ORDER BY x.order_count DESC;
