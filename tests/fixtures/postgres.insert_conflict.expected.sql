INSERT INTO order_audit (id, code) VALUES (1, 'P001') ON CONFLICT(id) DO UPDATE SET code = excluded.code RETURNING id;
