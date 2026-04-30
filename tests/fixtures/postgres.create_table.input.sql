create table order_audit (id bigint primary key, code varchar(64) not null, payload jsonb, created_at timestamptz default now());
