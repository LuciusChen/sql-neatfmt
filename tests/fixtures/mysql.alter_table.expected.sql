ALTER TABLE ffp_order_payoil
  ADD COLUMN audit_status tinyint(1) NOT NULL DEFAULT 0 comment '审核状态',
  ADD INDEX idx_customer_time (customer_id, create_time),
  DROP COLUMN old_flag;
