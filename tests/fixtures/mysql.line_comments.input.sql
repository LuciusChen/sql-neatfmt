select a.id, b.code
from table_a a
left join table_b b on a.id = b.a_id -- and b.deleted = 0
where a.status = 1
  -- and a.deleted = 0
group by a.id;
