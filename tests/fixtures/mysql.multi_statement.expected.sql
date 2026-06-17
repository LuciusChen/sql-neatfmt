SELECT * FROM `demo`.`ws_sale_order` WHERE sale_order_code = 'ORD-0001';
SELECT a.id,
       a.name
FROM table_a a
WHERE a.status = 1
  AND a.deleted = 0;
