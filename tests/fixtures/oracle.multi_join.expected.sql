SELECT op.code,
       c.customer_name,
       g.goods_name
FROM order_payoil op
         INNER JOIN customer c ON c.customer_id = op.customer_id
         LEFT JOIN goods g
           ON g.goods_id = op.goods_id
          AND g.deleted = 0
WHERE op.deleted = 0;
