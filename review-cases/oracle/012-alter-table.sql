alter table order_payoil add audit_status varchar2(20) default 'NEW' not null, add reviewed_at timestamp null, add constraint chk_order_payoil_amount check (amount >= 0);
