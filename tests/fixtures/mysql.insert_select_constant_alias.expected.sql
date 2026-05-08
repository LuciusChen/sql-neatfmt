INSERT INTO cap_customer_settlement_history (customer_id, state, subject_id)
SELECT customer_id,
       state,
       17 AS subject_id
FROM cap_customer_settlement_history_temp;
