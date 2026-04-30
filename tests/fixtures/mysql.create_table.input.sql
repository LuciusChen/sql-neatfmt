create table order_audit (id bigint primary key, payoil_code varchar(64) not null, created_at datetime default current_timestamp);
