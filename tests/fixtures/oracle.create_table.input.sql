create table order_audit (id number primary key, code varchar2(64) not null, created_at date default sysdate);
