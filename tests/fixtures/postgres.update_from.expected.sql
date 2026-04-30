UPDATE order_payoil op
SET deleted = TRUE
FROM customer c
WHERE c.customer_id = op.customer_id
  AND c.disabled = TRUE
RETURNING op.id;
