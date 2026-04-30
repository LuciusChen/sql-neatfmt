merge into target t using source s on (t.id = s.id) when matched then update set t.name = s.name when not matched then insert (id, name) values (s.id, s.name);
