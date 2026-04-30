SELECT a.id,
       a.name
FROM table_a a
WHERE a.status = 1
ORDER BY a.id
FETCH FIRST 10 ROWS ONLY;
