select customer_id, decode(status, 'A', 'ACTIVE', 'I', 'INACTIVE', 'UNKNOWN') status_name, nvl(balance, 0) balance from customer where created_at >= to_date('2026-04-01', 'YYYY-MM-DD');
