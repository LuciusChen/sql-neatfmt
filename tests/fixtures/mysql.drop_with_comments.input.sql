-- temp cleanup
drop table cap_customer_settlement_history_temp;
-- long insert
insert into cap_sale_subject (subject_id, subject_name, subject_abbreviation, subject_code, subject_order_direction, subject_goods_direction, vice_goods_direction, subject_properties, subject_state, create_time, create_user_id, update_time, update_user_id, remarks, is_incor_capital_system, subject_cate) values (16, '南京兆基实业有限公司兴隆洲加油站', '兆基兴隆洲', null, 79, 79, 128, 81, 84, now(), 1, now(), 1, null, '1', 1);
select *
from `zj`.`ffp_cust_oil_stora`;
