SELECT CustomerName,
       IFNULL(DATE_FORMAT(foc.create_time, '%Y-%m-%d'), 'unknown') CreateDate
FROM ffp_order_consign foc
WHERE DATE_FORMAT(foc.create_time, '%Y-%m-%d') >= '2026-04-27'
  AND DATE_FORMAT(foc.create_time, '%Y-%m-%d') <= '2026-04-29'
GROUP BY DATE_FORMAT(foc.create_time, '%Y-%m-%d')
ORDER BY CreateDate;
