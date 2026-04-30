select a.id, a.name, b.code code_name from table_a a left join table_b b on a.id = b.a_id and b.deleted = false where a.status = 1 and a.create_time >= date '2026-04-27' order by a.id desc;

