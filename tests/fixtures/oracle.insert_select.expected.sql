INSERT INTO order_archive (id, code, create_time)
SELECT id,
       code,
       SYSDATE
FROM order_payoil
WHERE create_time >= TO_DATE('2026-04-01', 'YYYY-MM-DD')
  AND deleted = 0;
