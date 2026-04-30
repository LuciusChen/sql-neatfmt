select x.customer_id, x.order_count from (select customer_id, count(*) order_count from order_payoil where deleted = 0 group by customer_id) x where x.order_count > 1 order by x.order_count desc;
