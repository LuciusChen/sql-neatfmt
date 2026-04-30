SELECT code
FROM order_payoil
WHERE create_time BETWEEN CAST('2026-04-01' AS DATE) AND CAST('2026-04-30' AS DATE)
  AND code LIKE 'P%'
  AND oil_site_id IN (1, 2, 3);
