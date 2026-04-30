INSERT INTO order_audit (id, code, customer_id, oil_site_id, goods_id, create_time, update_time, payload)
VALUES (1, 'P001', 1001, 12, 9, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CAST('{"source":"manual","comment":"very long payload for checking insert values wrapping"}' AS JSONB))
RETURNING id, code;
