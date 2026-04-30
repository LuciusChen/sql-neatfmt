SELECT fop.payoil_code,
       (SELECT COUNT(1)
        FROM ffp_cust_oil_stora_his AS h
        WHERE h.plan_code = fop.payoil_code
          AND h.update_oil_num > 0) AS history_count
FROM ffp_order_payoil fop
WHERE EXISTS (SELECT 1 FROM ffp_order_consign AS foc WHERE foc.order_id = fop.payoil_id AND foc.deleted = 0);
