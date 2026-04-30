SELECT a.id,
       a.name,
       b.code code_name
FROM table_a a
         LEFT JOIN table_b b
           ON a.id = b.a_id
          AND b.deleted = 0
WHERE a.status = 1
  AND a.create_time >= '2026-04-27'
  AND a.create_time < '2026-04-30'
GROUP BY a.id
ORDER BY a.id DESC;
