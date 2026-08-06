from __future__ import annotations

import pandas as pd

from .base import Strategy


class BuyAndHoldStrategy(Strategy):
    name = "buy_and_hold"

    def generate_signals(self, bars: pd.DataFrame) -> pd.Series:
        signal = pd.Series(1.0, index=bars.index, name="target_position")
        if not signal.empty:
            signal.iloc[0] = 0.0
        return signal
