SELECT payoil_code
FROM ffp_order_payoil
WHERE create_time BETWEEN '2026-04-01' AND '2026-04-30'
  AND payoil_code LIKE 'P%'
  AND oil_site_id IN (1, 2, 3);
