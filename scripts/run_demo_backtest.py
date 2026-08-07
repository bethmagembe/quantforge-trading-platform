from __future__ import annotations

import json

from trading_system.config import BacktestConfig
from trading_system.data import generate_daily_market_data
from trading_system.engine import Backtester
from trading_system.strategies import SMACrossoverStrategy


def main() -> None:
    bars = generate_daily_market_data(years=5, seed=42)
    result = Backtester(BacktestConfig(initial_capital=100_000, commission_bps=2, slippage_bps=1)).run(
        bars, SMACrossoverStrategy(short_window=20, long_window=100)
    )
    print(json.dumps(result.summary(), indent=2, default=str))


if __name__ == "__main__":
    main()
