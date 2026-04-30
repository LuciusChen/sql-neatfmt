SELECT customer_id,
       DECODE(status, 'A', 'ACTIVE', 'I', 'INACTIVE', 'UNKNOWN') status_name,
       NVL(balance, 0)                                           balance
FROM customer
WHERE created_at >= TO_DATE('2026-04-01', 'YYYY-MM-DD');
