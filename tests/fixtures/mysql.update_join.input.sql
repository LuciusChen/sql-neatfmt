update ffp_order_payoil fop left join ffp_order_consign foc on fop.payoil_id = foc.order_id and foc.deleted = 0 set fop.oil_site_id = foc.oil_site_id, fop.update_time = now() where fop.payoil_code = 'P001' and fop.deleted = 0;

