DELETE FROM order_payoil
WHERE payoil_code = 'P001'
  AND deleted = TRUE
RETURNING payoil_id;
