INSERT INTO ffp_order_payoil (payoil_code, customer_id, oil_site_id, create_time)
SELECT CONCAT('P', foc.order_id),
       foc.customer_id,
       foc.oil_site_id,
       NOW()
FROM ffp_order_consign foc
WHERE foc.create_time >= '2026-04-01'
  AND foc.deleted = 0;
