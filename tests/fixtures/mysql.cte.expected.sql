WITH
  recent_order AS (
    SELECT payoil_id,
           payoil_code,
           customer_id
    FROM ffp_order_payoil
    WHERE create_time >= '2026-04-01'
      AND deleted = 0
  )
SELECT ro.payoil_code,
       cc.customer_name
FROM recent_order ro
         LEFT JOIN cap_customer cc ON cc.customer_id = ro.customer_id
WHERE cc.customer_name IS NOT NULL
ORDER BY ro.payoil_id DESC;
