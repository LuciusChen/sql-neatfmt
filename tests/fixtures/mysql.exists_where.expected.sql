SELECT customer_id
FROM cap_customer cc
WHERE EXISTS (SELECT 1 FROM ffp_order_payoil AS fop WHERE fop.customer_id = cc.customer_id AND fop.deleted = 0);
