alter table ffp_order_payoil add column audit_status tinyint(1) not null default 0 comment 'audit status', add index idx_customer_time (customer_id, create_time), drop column old_flag;

