INSERT INTO order_archive (id, code, create_time)
SELECT id,
       code,
       CURRENT_TIMESTAMP
FROM order_payoil
WHERE create_time >= CAST('2026-04-01' AS DATE)
  AND deleted = FALSE
RETURNING id, code;
