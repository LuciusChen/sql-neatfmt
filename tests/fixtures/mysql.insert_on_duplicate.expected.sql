INSERT INTO order_audit (id, payoil_code)
VALUES (1, 'P001')
ON DUPLICATE KEY UPDATE payoil_code = VALUES(payoil_code), created_at = NOW();
