UPDATE orders
SET status     = 'paid',
    updated_at = CURRENT_TIMESTAMP
WHERE id = $1
  AND status = 'pending'
RETURNING id,
    status,
    updated_at;
