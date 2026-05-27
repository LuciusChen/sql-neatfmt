SELECT * FROM table_a a INNER table_b b ON a.id = b.a_id CROSS table_c c LEFT OUTER table_d d ON d.id = a.d_id;
