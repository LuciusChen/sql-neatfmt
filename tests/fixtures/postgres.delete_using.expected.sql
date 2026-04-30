DELETE FROM order_payoil op
USING customer c
WHERE c.customer_id = op.customer_id
  AND c.disabled = TRUE
RETURNING op.id;
