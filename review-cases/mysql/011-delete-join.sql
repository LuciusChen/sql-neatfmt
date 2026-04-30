delete fop from ffp_order_payoil fop left join ffp_order_consign foc on fop.payoil_id = foc.order_id where foc.order_id is null and fop.create_time < '2026-01-01';
