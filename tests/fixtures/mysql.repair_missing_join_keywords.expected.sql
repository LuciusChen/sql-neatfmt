SELECT *
FROM table_a a
         INNER JOIN table_b b ON a.id = b.a_id
         CROSS JOIN table_c c
         LEFT OUTER JOIN table_d d ON d.id = a.d_id;
