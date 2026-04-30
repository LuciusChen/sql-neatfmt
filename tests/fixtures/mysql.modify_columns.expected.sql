ALTER TABLE zj_test.ffp_order_payoil
  modify COLUMN invite_customer_type_id SMALLINT(6) NULL comment '邀请客户类型：1老客，2新客',
  modify COLUMN invite_customer_id VARCHAR(100) NULL comment '邀请客户名称，用户自由填写';
