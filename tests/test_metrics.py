import pandas as pd

from trading_system.engine.metrics import calculate_metrics, max_drawdown


def test_max_drawdown() -> None:
    equity = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert max_drawdown(equity) == -0.25


def test_metrics_include_risk_and_return_fields() -> None:
    returns = pd.Series([0.0, 0.01, -0.005, 0.02, -0.01])
    equity = 100_000 * (1 + returns).cumprod()
    metrics = calculate_metrics(returns, equity, trade_count=3)
    assert metrics["trade_count"] == 3
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "max_drawdown" in metrics
