select customer_id from cap_customer cc where exists (select 1 from ffp_order_payoil fop where fop.customer_id = cc.customer_id and fop.deleted = 0);
