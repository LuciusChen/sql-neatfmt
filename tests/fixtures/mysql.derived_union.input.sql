SELECT customer_id,
       customer_name,
       codes,
       subject_id,
       salesman_id,
       subject_abbreviation,
       settlement_mode,
       settlement_mode2,
       salesman_name,
       fixed_fund,
       credit_line,
       contract_payment_month,
       settlement_date_number,
       settlement_date_mode,
       contract_payment_date_mode,
       contract_payment_date_number,
       enterprise_nature,
       reimbursement_time,
       ship_agency,
       isCRM
FROM (SELECT cc.customer_id AS customer_id, cc.customer_name AS customer_name, o.sale_order_code AS codes, o.subject_id AS subject_id, o.salesman_id AS salesman_id, css.subject_abbreviation AS subject_abbreviation, ct.settlement_mode AS settlement_mode, ct.settlement_mode2 AS settlement_mode2, ct.salesman_name AS salesman_name, ct.fixed_fund AS fixed_fund, ct.credit_line AS credit_line, ct.contract_payment_month AS contract_payment_month, ct.settlement_date_number AS settlement_date_number, ct.settlement_date_mode AS settlement_date_mode, ct.contract_payment_date_mode AS contract_payment_date_mode, ct.contract_payment_date_number AS contract_payment_date_number, cc.enterprise_nature AS enterprise_nature, o.reimbursement_time AS reimbursement_time, o.ship_agency AS ship_agency, CASE WHEN NOT ccm.crm_customer_id IS NULL THEN 1 ELSE 0 END AS isCRM FROM cap_sale_order AS o LEFT JOIN cap_customer AS cc ON cc.customer_id = o.customer_id LEFT JOIN crm_customer AS ccm ON cc.customer_id = ccm.cap_customer_id LEFT JOIN cap_customer_configure AS ccc ON ccc.customer_id = o.customer_id AND ccc.subject_id = o.subject_id LEFT JOIN cap_customer_settlement_history AS ct ON ct.customer_id = o.customer_id AND ct.subject_id = o.subject_id LEFT JOIN cap_sale_subject AS css ON css.subject_id = o.subject_id LEFT JOIN t_user_section AS usn ON usn.user_id = ct.salesman_id WHERE ct.state = 1 AND NOT ccc.id IS NULL AND ccc.state = 0 UNION ALL SELECT cc.customer_id AS customer_id, cc.customer_name, '' AS codes, o.subject_id AS subject_id, o.salesman_id AS salesman_id, css.subject_abbreviation AS subject_abbreviation, ct.settlement_mode AS settlement_mode, ct.settlement_mode2 AS settlement_mode2, ct.salesman_name AS salesman_name, ct.fixed_fund AS fixed_fund, ct.credit_line AS credit_line, ct.contract_payment_month AS contract_payment_month, ct.settlement_date_number AS settlement_date_number, ct.settlement_date_mode AS settlement_date_mode, ct.contract_payment_date_mode AS contract_payment_date_mode, ct.contract_payment_date_number AS contract_payment_date_number, cc.enterprise_nature AS enterprise_nature, o.income_time AS reimbursement_time, o.ship_agency AS ship_agency, CASE WHEN ccm.crm_customer_id IS NULL AND o.subject_id = 1 THEN 0 ELSE 1 END AS isCRM FROM cap_income_order AS o LEFT JOIN cap_customer_configure AS ccc ON ccc.customer_id = o.customer_id AND ccc.subject_id = o.subject_id LEFT JOIN cap_customer AS cc ON cc.customer_id = o.customer_id LEFT JOIN crm_customer AS ccm ON cc.customer_id = ccm.cap_customer_id LEFT JOIN cap_customer_settlement_history AS ct ON ct.customer_id = o.customer_id AND ct.subject_id = o.subject_id LEFT JOIN cap_sale_subject AS css ON css.subject_id = o.subject_id LEFT JOIN t_user_section AS usn ON usn.user_id = ct.salesman_id WHERE o.state = 1 AND ct.state = 1 AND NOT ccc.id IS NULL AND ccc.state = 0) ref
WHERE 1 = 1
  AND locate('重庆市巫山县源林水陆运输有限公司', customer_name) > 0
GROUP BY customer_name, subject_id
ORDER BY CAST(customer_name AS CHAR CHARACTER SET GBK), subject_id ASC;
