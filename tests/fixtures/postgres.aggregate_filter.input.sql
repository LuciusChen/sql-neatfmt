select customer_id, count(*) filter (where deleted = false) active_count from order_payoil group by customer_id having count(*) > 1;
