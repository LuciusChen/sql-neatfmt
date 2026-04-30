SELECT customer_id,
       DECODE(deleted, 1, 'deleted', 'active') status_name
FROM order_payoil
WHERE code LIKE 'P%';
