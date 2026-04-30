select a.id, a.name, nvl(b.code, 'N/A') code_name from table_a a left join table_b b on a.id = b.a_id and b.deleted = 0 where a.status = 1 order by a.id desc;

