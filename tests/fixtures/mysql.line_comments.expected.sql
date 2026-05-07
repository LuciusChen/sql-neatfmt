SELECT a.id,
       b.code
FROM table_a a
         LEFT JOIN table_b b ON a.id = b.a_id -- and b.deleted = 0
WHERE a.status = 1
  -- and a.deleted = 0
GROUP BY a.id;
