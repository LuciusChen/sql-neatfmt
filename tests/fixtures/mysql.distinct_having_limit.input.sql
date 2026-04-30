select distinct customer_id, oil_site_id from ffp_order_payoil where deleted = 0 group by customer_id, oil_site_id having count(1) > 1 order by customer_id desc limit 10 offset 20;
