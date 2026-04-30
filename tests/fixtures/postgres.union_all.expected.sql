SELECT id FROM order_payoil WHERE deleted = FALSE
UNION ALL
SELECT order_id FROM order_consign WHERE deleted = FALSE
ORDER BY id;
