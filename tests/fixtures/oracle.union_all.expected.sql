SELECT id FROM order_payoil WHERE deleted = 0
UNION ALL
SELECT order_id FROM order_consign WHERE deleted = 0
ORDER BY id;
