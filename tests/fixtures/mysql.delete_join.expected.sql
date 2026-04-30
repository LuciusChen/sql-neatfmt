DELETE fop
FROM ffp_order_payoil fop
         LEFT JOIN ffp_order_consign foc ON foc.order_id = fop.payoil_id
WHERE foc.deleted = 1;
