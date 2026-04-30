delete from orders o using customers c where c.id = o.customer_id and c.status = 'INACTIVE' and o.created_at < date '2026-04-01' returning o.id, o.code, o.status;
