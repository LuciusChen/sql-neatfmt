MERGE INTO customer_summary t
USING (SELECT customer_id, SUM(amount) AS amount
       FROM orders
       WHERE created_at >= TO_DATE('2026-04-01', 'YYYY-MM-DD')
       GROUP BY customer_id) s
ON (t.customer_id = s.customer_id)
WHEN MATCHED THEN
    UPDATE
    SET t.amount     = s.amount,
        t.updated_at = SYSDATE
WHEN NOT MATCHED THEN
    INSERT (customer_id, amount, updated_at)
    VALUES (s.customer_id, s.amount, SYSDATE);
