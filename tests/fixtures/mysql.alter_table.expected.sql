ALTER TABLE ffp_order_payoil
  ADD COLUMN audit_status TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'audit status',
  ADD INDEX idx_customer_time (customer_id, create_time),
  DROP COLUMN old_flag;
