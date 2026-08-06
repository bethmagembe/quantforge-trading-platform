import pandas as pd

from trading_system.alerts import evaluate_market_alerts, evaluate_portfolio_alerts


def test_large_price_move_alert() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2),
            "symbol": ["TEST", "TEST"],
            "close": [100.0, 111.0],
            "volume": [1000, 1000],
        }
    )
    alerts = evaluate_market_alerts(bars, price_move_threshold=0.10)
    assert any(alert.rule == "large_price_move" for alert in alerts)


def test_drawdown_alert() -> None:
    equity = pd.DataFrame({"drawdown": [-0.02, -0.12]})
    alerts = evaluate_portfolio_alerts(equity, drawdown_threshold=-0.10)
    assert alerts[0].rule == "portfolio_drawdown"
