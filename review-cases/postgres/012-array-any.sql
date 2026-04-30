select id, code, amount from orders where status = any(array['paid', 'pending']) and customer_id = any(array[1, 2, 3]) and amount between 0 and 500 order by id;
