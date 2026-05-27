SELECT fop.payoil_code,
       cc.customer_name,
       fg.goods_name
FROM ffp_order_payoil fop
         INNER JOIN cap_customer cc ON cc.customer_id = fop.customer_id
         LEFT JOIN ffp_goods fg
           ON fg.goods_id = fop.goods_id
          AND fg.deleted = 0
WHERE fop.deleted = 0;
