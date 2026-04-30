select distinct customer_id, oil_site_id from order_payoil where deleted = false group by customer_id, oil_site_id having count(*) > 1 order by customer_id desc limit 10 offset 20;
