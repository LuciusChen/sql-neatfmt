SELECT x.customer_id,
       x.order_count
FROM (SELECT customer_id, COUNT(1) AS order_count FROM ffp_order_payoil WHERE deleted = 0 GROUP BY customer_id) x
WHERE x.order_count > 1
ORDER BY x.order_count DESC;
