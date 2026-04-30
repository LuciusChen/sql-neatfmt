delete fop from ffp_order_payoil fop left join ffp_order_consign foc on foc.order_id = fop.payoil_id where foc.deleted = 1;
