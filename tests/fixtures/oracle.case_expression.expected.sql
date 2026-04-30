SELECT code,
       CASE WHEN deleted = 1 THEN 'deleted' WHEN oil_site_id IS NULL THEN 'missing' ELSE 'active' END status_name
FROM order_payoil
WHERE code LIKE 'P%'
  AND customer_id IN (1001, 1002);
