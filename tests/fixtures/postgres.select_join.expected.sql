SELECT a.id,
       a.name,
       b.code code_name
FROM table_a a
         LEFT JOIN table_b b
           ON a.id = b.a_id
          AND b.deleted = FALSE
WHERE a.status = 1
  AND a.create_time >= CAST('2026-04-27' AS DATE)
ORDER BY a.id DESC;
