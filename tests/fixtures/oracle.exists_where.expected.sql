SELECT customer_id
FROM customer c
WHERE EXISTS (SELECT 1 FROM order_payoil op WHERE op.customer_id = c.customer_id AND op.deleted = 0);
