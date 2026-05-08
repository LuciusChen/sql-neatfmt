insert into cap_customer_settlement_history (customer_id, state, subject_id)
select customer_id, state, 17 subject_id
from cap_customer_settlement_history_temp;
