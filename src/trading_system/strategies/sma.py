from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import Strategy


@dataclass
class SMACrossoverStrategy(Strategy):
    short_window: int = 20
    long_window: int = 100
    name: str = "sma_crossover"

    def __post_init__(self) -> None:
        if self.short_window <= 1:
            raise ValueError("short_window must be greater than 1")
        if self.long_window <= self.short_window:
            raise ValueError("long_window must be greater than short_window")

    def generate_signals(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"].astype(float)
        short_ma = close.rolling(self.short_window, min_periods=self.short_window).mean()
        long_ma = close.rolling(self.long_window, min_periods=self.long_window).mean()
        signal = (short_ma > long_ma).astype(float)
        return signal.where(long_ma.notna(), 0.0).rename("target_position")
