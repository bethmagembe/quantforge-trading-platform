import pytest

from trading_system.config import BacktestConfig
from trading_system.data import generate_daily_market_data
from trading_system.engine import Backtester
from trading_system.strategies import BuyAndHoldStrategy, SMACrossoverStrategy


def test_backtest_runs_across_multiple_assets() -> None:
    bars = generate_daily_market_data(years=1, seed=11)
    result = Backtester(BacktestConfig(initial_capital=50_000)).run(
        bars, SMACrossoverStrategy(short_window=10, long_window=30)
    )
    assert not result.equity_curve.empty
    assert result.asset_results["symbol"].nunique() == 5
    assert result.metrics["ending_equity"] > 0
    assert result.metrics["trade_count"] == len(result.trades)
    assert result.equity_curve["drawdown"].max() <= 1e-12


def test_execution_uses_next_bar_to_avoid_lookahead() -> None:
    bars = generate_daily_market_data(years=1, seed=5)
    result = Backtester().run(bars, BuyAndHoldStrategy())
    for _, group in result.asset_results.groupby("symbol"):
        ordered = group.sort_values("timestamp")
        assert ordered.iloc[0]["position"] == 0.0


def test_invalid_ohlc_is_rejected() -> None:
    bars = generate_daily_market_data(years=1).head(20).copy()
    bars.loc[bars.index[0], "low"] = bars.loc[bars.index[0], "high"] + 1
    with pytest.raises(ValueError, match="invalid OHLCV"):
        Backtester().run(bars, BuyAndHoldStrategy())
