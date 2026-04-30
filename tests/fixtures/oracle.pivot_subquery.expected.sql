SELECT *
FROM (SELECT customer_id, status, amount
      FROM order_payoil
      WHERE created_at >= TO_DATE('2026-04-01', 'YYYY-MM-DD')) PIVOT (SUM(amount) FOR status IN ('PAID' AS paid_amount, 'PENDING' AS pending_amount, 'CANCELLED' AS cancelled_amount))
ORDER BY customer_id;
