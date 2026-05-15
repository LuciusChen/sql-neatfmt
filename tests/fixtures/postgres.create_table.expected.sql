CREATE TABLE order_audit
(
    id         BIGINT      PRIMARY KEY,
    code       VARCHAR(64) NOT NULL,
    payload    JSONB,
    created_at TIMESTAMPTZ          DEFAULT CURRENT_TIMESTAMP
);
