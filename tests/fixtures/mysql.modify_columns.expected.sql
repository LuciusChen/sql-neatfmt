ALTER TABLE zj_test.ffp_order_payoil
  MODIFY COLUMN invite_customer_type_id SMALLINT(6) NULL COMMENT '邀请客户类型：1老客，2新客',
  MODIFY COLUMN invite_customer_id VARCHAR(100) NULL COMMENT '邀请客户名称，用户自由填写';
