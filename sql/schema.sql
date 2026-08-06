-- PostgreSQL schema for the portfolio trading platform.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS assets (
    asset_id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(200),
    asset_class VARCHAR(50) NOT NULL,
    exchange VARCHAR(50),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    ingestion_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
    rows_received BIGINT NOT NULL DEFAULT 0,
    rows_inserted BIGINT NOT NULL DEFAULT 0,
    rows_rejected BIGINT NOT NULL DEFAULT 0,
    details JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE IF NOT EXISTS market_bars (
    asset_id BIGINT NOT NULL REFERENCES assets(asset_id),
    bar_time TIMESTAMPTZ NOT NULL,
    interval VARCHAR(10) NOT NULL DEFAULT '1d',
    open NUMERIC(20,8) NOT NULL CHECK (open > 0),
    high NUMERIC(20,8) NOT NULL CHECK (high > 0),
    low NUMERIC(20,8) NOT NULL CHECK (low > 0),
    close NUMERIC(20,8) NOT NULL CHECK (close > 0),
    volume NUMERIC(24,4) NOT NULL CHECK (volume >= 0),
    source VARCHAR(100) NOT NULL,
    ingestion_run_id UUID REFERENCES ingestion_runs(ingestion_run_id),
    PRIMARY KEY (asset_id, bar_time, interval),
    CHECK (low <= LEAST(open, close, high)),
    CHECK (high >= GREATEST(open, close, low))
);
CREATE INDEX IF NOT EXISTS idx_market_bars_time ON market_bars(bar_time DESC);
CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_time ON market_bars(asset_id, bar_time DESC);

CREATE TABLE IF NOT EXISTS strategies (
    strategy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(30) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    backtest_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    initial_capital NUMERIC(20,2) NOT NULL,
    commission_bps NUMERIC(8,4) NOT NULL DEFAULT 0,
    slippage_bps NUMERIC(8,4) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
    data_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID REFERENCES backtest_runs(backtest_run_id),
    asset_id BIGINT NOT NULL REFERENCES assets(asset_id),
    submitted_at TIMESTAMPTZ NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type VARCHAR(20) NOT NULL DEFAULT 'MARKET',
    quantity NUMERIC(24,8) NOT NULL CHECK (quantity > 0),
    limit_price NUMERIC(20,8),
    status VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(order_id),
    backtest_run_id UUID REFERENCES backtest_runs(backtest_run_id),
    asset_id BIGINT NOT NULL REFERENCES assets(asset_id),
    executed_at TIMESTAMPTZ NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY','SELL')),
    quantity NUMERIC(24,8) NOT NULL CHECK (quantity > 0),
    execution_price NUMERIC(20,8) NOT NULL CHECK (execution_price > 0),
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage_cost NUMERIC(20,8) NOT NULL DEFAULT 0,
    realized_pnl NUMERIC(20,8)
);
CREATE INDEX IF NOT EXISTS idx_trades_run_time ON trades(backtest_run_id, executed_at);

CREATE TABLE IF NOT EXISTS positions (
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(backtest_run_id),
    asset_id BIGINT NOT NULL REFERENCES assets(asset_id),
    snapshot_time TIMESTAMPTZ NOT NULL,
    quantity NUMERIC(24,8) NOT NULL,
    average_cost NUMERIC(20,8),
    market_price NUMERIC(20,8),
    market_value NUMERIC(20,8),
    unrealized_pnl NUMERIC(20,8),
    PRIMARY KEY (backtest_run_id, asset_id, snapshot_time)
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(backtest_run_id),
    snapshot_time TIMESTAMPTZ NOT NULL,
    cash NUMERIC(20,8) NOT NULL,
    gross_exposure NUMERIC(20,8) NOT NULL,
    net_exposure NUMERIC(20,8) NOT NULL,
    portfolio_value NUMERIC(20,8) NOT NULL,
    daily_return NUMERIC(16,10),
    drawdown NUMERIC(16,10),
    PRIMARY KEY (backtest_run_id, snapshot_time)
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(backtest_run_id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(24,10) NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (backtest_run_id, metric_name)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity VARCHAR(20) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    asset_id BIGINT REFERENCES assets(asset_id),
    backtest_run_id UUID REFERENCES backtest_runs(backtest_run_id),
    message TEXT NOT NULL,
    observed_value NUMERIC(24,10),
    threshold_value NUMERIC(24,10),
    acknowledged_at TIMESTAMPTZ
);
