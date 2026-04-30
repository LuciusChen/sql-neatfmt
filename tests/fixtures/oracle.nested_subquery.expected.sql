SELECT c.customer_name,
       (SELECT COUNT(*)
        FROM order_payoil op
        WHERE op.customer_id = c.customer_id AND op.deleted = 0) AS order_count
FROM customer c
WHERE EXISTS (SELECT 1 FROM order_payoil op2 WHERE op2.customer_id = c.customer_id AND op2.deleted = 0);
