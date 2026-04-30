INSERT INTO order_audit (id, code, customer_id, oil_site_id, goods_id, create_time, update_time, remark)
VALUES (1, 'P001', 1001, 12, 9, SYSDATE, SYSDATE, 'very long remark for checking insert values wrapping');
