alter table orders add column audit_status text not null default 'new', add column reviewed_at timestamptz null, add constraint chk_orders_amount_nonnegative check (amount >= 0);
