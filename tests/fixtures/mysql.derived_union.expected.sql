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
FROM (SELECT cc.customer_id                                              customer_id,
             cc.customer_name                                            customer_name,
             o.sale_order_code                                           codes,
             o.subject_id                                                subject_id,
             o.salesman_id                                               salesman_id,
             css.subject_abbreviation                                    subject_abbreviation,
             ct.settlement_mode                                          settlement_mode,
             ct.settlement_mode2                                         settlement_mode2,
             ct.salesman_name                                            salesman_name,
             ct.fixed_fund                                               fixed_fund,
             ct.credit_line                                              credit_line,
             ct.contract_payment_month                                   contract_payment_month,
             ct.settlement_date_number                                   settlement_date_number,
             ct.settlement_date_mode                                     settlement_date_mode,
             ct.contract_payment_date_mode                               contract_payment_date_mode,
             ct.contract_payment_date_number                             contract_payment_date_number,
             cc.enterprise_nature                                        enterprise_nature,
             o.reimbursement_time                                        reimbursement_time,
             o.ship_agency                                               ship_agency,
             CASE WHEN NOT ccm.crm_customer_id IS NULL THEN 1 ELSE 0 END isCRM
      FROM cap_sale_order o
               LEFT JOIN cap_customer cc ON cc.customer_id = o.customer_id
               LEFT JOIN crm_customer ccm ON cc.customer_id = ccm.cap_customer_id
               LEFT JOIN cap_customer_configure ccc
                 ON ccc.customer_id = o.customer_id
                AND ccc.subject_id = o.subject_id
               LEFT JOIN cap_customer_settlement_history ct
                 ON ct.customer_id = o.customer_id
                AND ct.subject_id = o.subject_id
               LEFT JOIN cap_sale_subject css ON css.subject_id = o.subject_id
               LEFT JOIN t_user_section usn ON usn.user_id = ct.salesman_id
      WHERE ct.state = 1
        AND ccc.id IS NOT NULL
        AND ccc.state = 0
      UNION ALL
      SELECT cc.customer_id                                                               customer_id,
             cc.customer_name,
             ''                                                                           AS codes,
             o.subject_id                                                                 subject_id,
             o.salesman_id                                                                salesman_id,
             css.subject_abbreviation                                                     subject_abbreviation,
             ct.settlement_mode                                                           settlement_mode,
             ct.settlement_mode2                                                          settlement_mode2,
             ct.salesman_name                                                             salesman_name,
             ct.fixed_fund                                                                fixed_fund,
             ct.credit_line                                                               credit_line,
             ct.contract_payment_month                                                    contract_payment_month,
             ct.settlement_date_number                                                    settlement_date_number,
             ct.settlement_date_mode                                                      settlement_date_mode,
             ct.contract_payment_date_mode                                                contract_payment_date_mode,
             ct.contract_payment_date_number                                              contract_payment_date_number,
             cc.enterprise_nature                                                         enterprise_nature,
             o.income_time                                                                reimbursement_time,
             o.ship_agency                                                                ship_agency,
             CASE WHEN ccm.crm_customer_id IS NULL AND o.subject_id = 1 THEN 0 ELSE 1 END isCRM
      FROM cap_income_order o
               LEFT JOIN cap_customer_configure ccc
                 ON ccc.customer_id = o.customer_id
                AND ccc.subject_id = o.subject_id
               LEFT JOIN cap_customer cc ON cc.customer_id = o.customer_id
               LEFT JOIN crm_customer ccm ON cc.customer_id = ccm.cap_customer_id
               LEFT JOIN cap_customer_settlement_history ct
                 ON ct.customer_id = o.customer_id
                AND ct.subject_id = o.subject_id
               LEFT JOIN cap_sale_subject css ON css.subject_id = o.subject_id
               LEFT JOIN t_user_section usn ON usn.user_id = ct.salesman_id
      WHERE o.state = 1
        AND ct.state = 1
        AND ccc.id IS NOT NULL
        AND ccc.state = 0) ref
WHERE 1 = 1
  AND LOCATE('Acme Logistics Co.', customer_name) > 0
GROUP BY customer_name, subject_id
ORDER BY CAST(customer_name AS CHAR CHARACTER SET GBK), subject_id ASC;
