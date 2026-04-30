insert into order_audit (id, payoil_code) values (1, 'P001') on duplicate key update payoil_code = values(payoil_code), created_at = now();
