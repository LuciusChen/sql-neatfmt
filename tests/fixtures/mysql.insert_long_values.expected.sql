INSERT INTO ffp_order_payoil (
    payoil_code,
    customer_id,
    oil_site_id,
    goods_id,
    plan_code,
    create_time,
    update_time,
    remark
)
VALUES (
    'P001',
    1001,
    12,
    9,
    'PLAN-20260430-0001',
    NOW(),
    NOW(),
    'very long remark for checking insert values wrapping'
);
