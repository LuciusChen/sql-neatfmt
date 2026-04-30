UPDATE order_payoil
SET oil_site_id = 12,
    update_time = SYSDATE
WHERE payoil_code = 'P001'
  AND deleted = 0;
