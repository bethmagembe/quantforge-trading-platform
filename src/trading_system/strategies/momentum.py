from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import Strategy


@dataclass
class MomentumStrategy(Strategy):
    lookback: int = 63
    threshold: float = 0.0
    name: str = "momentum"

    def __post_init__(self) -> None:
        if self.lookback <= 1:
            raise ValueError("lookback must be greater than 1")

    def generate_signals(self, bars: pd.DataFrame) -> pd.Series:
        momentum = bars["close"].astype(float).pct_change(self.lookback)
        return (momentum > self.threshold).astype(float).fillna(0.0).rename("target_position")
