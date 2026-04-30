delete from order_payoil op using customer c where c.customer_id = op.customer_id and c.disabled = true returning op.id;
