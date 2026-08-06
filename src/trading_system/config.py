from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_bps: float = 2.0
    slippage_bps: float = 1.0
    annualization_factor: int = 252
    allow_short: bool = False
    max_position_weight: float = 1.0

    @property
    def round_trip_cost_rate(self) -> float:
        return (self.commission_bps + self.slippage_bps) / 10_000.0

    def validate(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.commission_bps < 0 or self.slippage_bps < 0:
            raise ValueError("cost assumptions cannot be negative")
        if self.annualization_factor <= 0:
            raise ValueError("annualization_factor must be positive")
        if not 0 < self.max_position_weight <= 1:
            raise ValueError("max_position_weight must be in (0, 1]")
