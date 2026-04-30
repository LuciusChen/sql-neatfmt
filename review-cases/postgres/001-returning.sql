update orders set status = 'paid', updated_at = now() where id = $1 and status = 'pending' returning id, status, updated_at;
