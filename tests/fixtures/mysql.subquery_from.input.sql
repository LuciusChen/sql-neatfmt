select x.customer_id, x.order_count from (select customer_id, count(1) order_count from ffp_order_payoil where deleted = 0 group by customer_id) x where x.order_count > 1 order by x.order_count desc;
