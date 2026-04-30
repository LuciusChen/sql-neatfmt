UPDATE ffp_order_payoil fop
    LEFT JOIN ffp_order_consign foc
    ON fop.payoil_id = foc.order_id
        AND foc.deleted = 0
SET fop.oil_site_id = foc.oil_site_id,
    fop.update_time = NOW()
WHERE fop.payoil_code = 'P001'
  AND fop.deleted = 0;
