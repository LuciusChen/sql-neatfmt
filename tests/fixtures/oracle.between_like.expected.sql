SELECT code
FROM order_payoil
WHERE create_time BETWEEN TO_DATE('2026-04-01', 'YYYY-MM-DD') AND TO_DATE('2026-04-30', 'YYYY-MM-DD')
  AND code LIKE 'P%'
  AND oil_site_id IN (1, 2, 3);
