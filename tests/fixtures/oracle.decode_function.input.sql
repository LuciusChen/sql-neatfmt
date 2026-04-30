select customer_id, decode(deleted, 1, 'deleted', 'active') status_name from order_payoil where code like 'P%';
