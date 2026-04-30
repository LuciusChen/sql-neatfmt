select payoil_code from ffp_order_payoil where create_time between '2026-04-01' and '2026-04-30' and payoil_code like 'P%' and oil_site_id in (1, 2, 3);
