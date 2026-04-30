select customer_name, nvl(to_char(create_time, 'YYYY-MM-DD'), 'unknown') create_date from order_payoil where create_time >= date '2026-04-01' and deleted = 0 order by create_date;
