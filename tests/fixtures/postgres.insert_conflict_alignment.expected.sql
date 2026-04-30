INSERT INTO customer_account (customer_id, balance, updated_at)
VALUES ($1, $2, CURRENT_TIMESTAMP)
ON CONFLICT(customer_id) DO UPDATE SET balance    = excluded.balance,
                                       updated_at = CURRENT_TIMESTAMP
RETURNING customer_id, balance;
