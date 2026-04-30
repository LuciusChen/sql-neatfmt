MERGE INTO target t
USING source s
ON (t.id = s.id)
WHEN MATCHED THEN
    UPDATE
    SET t.name = s.name
WHEN NOT MATCHED THEN
    INSERT (id, name)
    VALUES (s.id, s.name);
