select distinct customer_id, oil_site_id from order_payoil where deleted = 0 order by customer_id offset 5 rows fetch next 10 rows only;
