SELECT c.customer_id,
       c.customer_name,
       x.order_count,
       x.total_amount
FROM customer c
         LEFT JOIN (SELECT customer_id, COUNT(*) AS order_count, SUM(amount) AS total_amount FROM order_payoil WHERE deleted = 0 GROUP BY customer_id) x ON x.customer_id = c.customer_id
WHERE c.status = 'ACTIVE'
  AND NVL(x.total_amount, 0) >= 0
ORDER BY x.total_amount DESC NULLS LAST;
