ALTER TABLE order_payoil
  ADD audit_code VARCHAR2(64),
  modify deleted DEFAULT 0;
