-- Latest portfolio performance by strategy.
SELECT
    s.name,
    s.version,
    br.backtest_run_id,
    br.period_start,
    br.period_end,
    MAX(CASE WHEN pm.metric_name = 'total_return' THEN pm.metric_value END) AS total_return,
    MAX(CASE WHEN pm.metric_name = 'sharpe_ratio' THEN pm.metric_value END) AS sharpe_ratio,
    MAX(CASE WHEN pm.metric_name = 'max_drawdown' THEN pm.metric_value END) AS max_drawdown
FROM backtest_runs br
JOIN strategies s USING (strategy_id)
LEFT JOIN performance_metrics pm USING (backtest_run_id)
WHERE br.status = 'SUCCEEDED'
GROUP BY s.name, s.version, br.backtest_run_id, br.period_start, br.period_end
ORDER BY br.completed_at DESC;

-- Rolling 20-session volatility by asset.
SELECT
    a.symbol,
    mb.bar_time,
    STDDEV_SAMP(LN(mb.close / LAG(mb.close) OVER (
        PARTITION BY mb.asset_id ORDER BY mb.bar_time
    ))) OVER (
        PARTITION BY mb.asset_id ORDER BY mb.bar_time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) * SQRT(252) AS annualized_volatility
FROM market_bars mb
JOIN assets a USING (asset_id)
WHERE mb.interval = '1d';

-- Daily turnover and transaction cost analysis.
SELECT
    DATE(t.executed_at) AS trade_date,
    COUNT(*) AS trade_count,
    SUM(t.quantity * t.execution_price) AS traded_notional,
    SUM(t.commission + t.slippage_cost) AS total_cost
FROM trades t
GROUP BY DATE(t.executed_at)
ORDER BY trade_date DESC;

-- Worst portfolio drawdowns.
SELECT
    backtest_run_id,
    snapshot_time,
    drawdown,
    portfolio_value
FROM portfolio_snapshots
ORDER BY drawdown ASC
LIMIT 20;

-- Asset exposure at the latest snapshot for each backtest.
WITH latest AS (
    SELECT backtest_run_id, MAX(snapshot_time) AS snapshot_time
    FROM positions
    GROUP BY backtest_run_id
)
SELECT
    p.backtest_run_id,
    a.symbol,
    p.market_value,
    p.market_value / NULLIF(SUM(p.market_value) OVER (PARTITION BY p.backtest_run_id), 0) AS portfolio_weight
FROM positions p
JOIN latest l USING (backtest_run_id, snapshot_time)
JOIN assets a USING (asset_id)
ORDER BY p.backtest_run_id, portfolio_weight DESC;
