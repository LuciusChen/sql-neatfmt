select customer_id, customer_name, created_at from customer where status = 'ACTIVE' order by created_at desc offset 20 rows fetch next 10 rows only;
