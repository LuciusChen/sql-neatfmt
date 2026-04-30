insert into order_audit (id, code) values (1, 'P001') on conflict (id) do update set code = excluded.code returning id;
