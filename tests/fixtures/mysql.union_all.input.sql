select payoil_id from ffp_order_payoil where deleted = 0 union all select order_id from ffp_order_consign where deleted = 0 order by payoil_id;
