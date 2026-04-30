select customer_id, payoil_code, row_number() over (partition by customer_id order by create_time desc) rn from ffp_order_payoil where deleted = 0;
