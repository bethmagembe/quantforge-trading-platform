from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import Strategy


@dataclass
class RSIMeanReversionStrategy(Strategy):
    window: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    name: str = "rsi_mean_reversion"

    def __post_init__(self) -> None:
        if self.window <= 1:
            raise ValueError("window must be greater than 1")
        if not 0 < self.oversold < self.overbought < 100:
            raise ValueError("RSI thresholds must satisfy 0 < oversold < overbought < 100")

    def generate_signals(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(self.window, min_periods=self.window).mean()
        loss = -delta.clip(upper=0).rolling(self.window, min_periods=self.window).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        target = pd.Series(np.nan, index=bars.index, dtype=float)
        target.loc[rsi < self.oversold] = 1.0
        target.loc[rsi > self.overbought] = 0.0
        return target.ffill().fillna(0.0).rename("target_position")
