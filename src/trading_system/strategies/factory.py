from __future__ import annotations

from .base import Strategy
from .buy_hold import BuyAndHoldStrategy
from .momentum import MomentumStrategy
from .rsi import RSIMeanReversionStrategy
from .sma import SMACrossoverStrategy


def create_strategy(name: str, **params: object) -> Strategy:
    normalized = name.strip().lower()
    if normalized in {"sma", "sma_crossover"}:
        return SMACrossoverStrategy(**params)
    if normalized in {"rsi", "rsi_mean_reversion"}:
        return RSIMeanReversionStrategy(**params)
    if normalized in {"momentum", "relative_momentum"}:
        return MomentumStrategy(**params)
    if normalized in {"buy_hold", "buy_and_hold"}:
        return BuyAndHoldStrategy()
    raise ValueError(f"Unknown strategy: {name}")
