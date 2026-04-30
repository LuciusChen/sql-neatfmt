select fop.payoil_code, (select count(1) from ffp_cust_oil_stora_his h where h.plan_code = fop.payoil_code and h.update_oil_num > 0) history_count from ffp_order_payoil fop where exists (select 1 from ffp_order_consign foc where foc.order_id = fop.payoil_id and foc.deleted = 0);

