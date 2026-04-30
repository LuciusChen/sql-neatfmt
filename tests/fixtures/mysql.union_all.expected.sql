SELECT payoil_id FROM ffp_order_payoil WHERE deleted = 0
UNION ALL
SELECT order_id FROM ffp_order_consign WHERE deleted = 0
ORDER BY payoil_id;
