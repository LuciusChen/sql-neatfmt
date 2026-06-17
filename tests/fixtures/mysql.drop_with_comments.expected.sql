-- temp cleanup
DROP TABLE cap_customer_settlement_history_temp;
-- long insert
INSERT INTO cap_sale_subject (subject_id, subject_name, subject_abbreviation, subject_code, subject_order_direction, subject_goods_direction, vice_goods_direction, subject_properties, subject_state, create_time, create_user_id, update_time, update_user_id, remarks, is_incor_capital_system, subject_cate)
VALUES (16, 'Acme Demo Station', 'Acme Station', NULL, 79, 79, 128, 81, 84, NOW(), 1, NOW(), 1, NULL, '1', 1);
SELECT * FROM `demo`.`ffp_cust_oil_stora`;
