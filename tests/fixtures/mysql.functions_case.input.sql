select CustomerName, ifnull(date_format(foc.create_time, '%Y-%m-%d'), 'unknown') CreateDate from ffp_order_consign foc where date_format(foc.create_time, '%Y-%m-%d') >= '2026-04-27' and date_format(foc.create_time, '%Y-%m-%d') <= '2026-04-29' group by date_format(foc.create_time, '%Y-%m-%d') order by CreateDate;

