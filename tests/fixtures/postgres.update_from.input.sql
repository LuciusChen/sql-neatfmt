update order_payoil op set deleted = true from customer c where c.customer_id = op.customer_id and c.disabled = true returning op.id;
