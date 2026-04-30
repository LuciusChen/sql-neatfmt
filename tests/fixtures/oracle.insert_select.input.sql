insert into order_archive (id, code, create_time) select id, code, sysdate from order_payoil where create_time >= date '2026-04-01' and deleted = 0;
