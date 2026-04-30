UPDATE order_payoil
SET oil_site_id = 12,
    update_time = CURRENT_TIMESTAMP
WHERE payoil_code = 'P001'
  AND deleted = FALSE
RETURNING id, update_time;
