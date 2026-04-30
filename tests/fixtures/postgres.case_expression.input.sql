select code, case when deleted = true then 'deleted' when oil_site_id is null then 'missing' else 'active' end status_name from order_payoil where code like 'P%' and customer_id in (1001, 1002);
