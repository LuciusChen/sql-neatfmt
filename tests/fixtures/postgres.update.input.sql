update order_payoil set oil_site_id = 12, update_time = now() where payoil_code = 'P001' and deleted = false returning id, update_time;
