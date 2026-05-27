select * from table_a a inner join table_b b on a.id = b.a_id cross join table_c c left outer join table_d d on d.id = a.d_id;
