ALTER TABLE demo_test.ffp_order_payoil
  MODIFY COLUMN invite_customer_type_id SMALLINT(6) NULL COMMENT 'customer type: 1 existing, 2 new',
  MODIFY COLUMN invite_customer_id VARCHAR(100) NULL COMMENT 'customer name entered by user';
