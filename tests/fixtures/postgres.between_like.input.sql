select code from order_payoil where create_time between date '2026-04-01' and date '2026-04-30' and code like 'P%' and oil_site_id in (1, 2, 3);
