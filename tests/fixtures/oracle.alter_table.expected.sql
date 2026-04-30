ALTER TABLE order_payoil
  ADD audit_code VARCHAR2(64),
  MODIFY deleted DEFAULT 0;
