UPDATE customer_summary cs
SET cs.total_amount = (SELECT SUM(op.amount)
                       FROM order_payoil op
                       WHERE op.customer_id = cs.customer_id
                         AND op.deleted = 0),
    cs.updated_at   = SYSDATE
WHERE EXISTS (SELECT 1
              FROM order_payoil op
              WHERE op.customer_id = cs.customer_id
                AND op.created_at >= TO_DATE('2026-04-01', 'YYYY-MM-DD'));
