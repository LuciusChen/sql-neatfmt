insert into ffp_order_payoil (payoil_code, customer_id, oil_site_id, create_time) select concat('P', foc.order_id), foc.customer_id, foc.oil_site_id, now() from ffp_order_consign foc where foc.create_time >= '2026-04-01' and foc.deleted = 0;

