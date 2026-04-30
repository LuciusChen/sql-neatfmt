select customer_id from customer c where exists (select 1 from order_payoil op where op.customer_id = c.customer_id and op.deleted = 0);
