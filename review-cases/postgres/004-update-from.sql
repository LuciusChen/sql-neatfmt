update orders o set customer_name = c.name, updated_at = now() from customers c where o.customer_id = c.id and o.customer_name is distinct from c.name returning o.id, o.customer_name;
