SELECT a.id,
       a.name,
       NVL(b.code, 'N/A') code_name
FROM table_a a
         LEFT JOIN table_b b
           ON a.id = b.a_id
          AND b.deleted = 0
WHERE a.status = 1
ORDER BY a.id DESC;
