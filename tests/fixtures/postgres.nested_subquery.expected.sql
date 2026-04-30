SELECT c.customer_name,
       (SELECT COUNT(*)
        FROM order_payoil AS op
        WHERE op.customer_id = c.customer_id AND op.deleted = FALSE) AS order_count
FROM customer c
WHERE EXISTS (SELECT 1 FROM order_payoil AS op2 WHERE op2.customer_id = c.customer_id AND op2.deleted = FALSE);
