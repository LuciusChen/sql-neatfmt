delete from order_audit oa where exists (select 1 from orders o where o.id = oa.order_id and o.status = 'pending') and oa.created_at < current_timestamp returning oa.id, oa.code;
