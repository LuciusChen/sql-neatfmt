select customer_id, code, row_number() over (partition by customer_id order by create_time desc) rn from order_payoil where deleted = false;
