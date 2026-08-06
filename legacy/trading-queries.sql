-- The original analytical query collection is retained for comparison.
-- See sql/analytics.sql for the redesigned PostgreSQL analytics layer.
SELECT stock_id,
       SUM(CASE WHEN type = 'SELL' THEN price * quantity
                WHEN type = 'BUY' THEN -price * quantity END) AS net_profit
FROM Transactions
GROUP BY stock_id;
