UPDATE accounts a
SET balance = balance - 100
WHERE a.id = 1
RETURNING a.id,
          a.balance;
