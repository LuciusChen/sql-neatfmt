delete from order_audit oa where exists (select 1 from order_payoil op where op.id = oa.order_id and op.deleted = 1) and oa.created_at < add_months(sysdate, -6);
