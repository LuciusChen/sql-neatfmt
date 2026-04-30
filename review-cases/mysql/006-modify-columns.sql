alter table zj_test.ffp_order_payoil modify column invite_customer_type_id smallint(6) null COMMENT '邀请客户类型：1老客，2新客', modify column invite_customer_id varchar(100) null COMMENT '邀请客户名称，用户自由填写';
