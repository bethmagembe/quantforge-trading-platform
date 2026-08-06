from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_system.config import BacktestConfig
from trading_system.strategies.base import Strategy
from .metrics import calculate_metrics


REQUIRED_COLUMNS = {
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


@dataclass
class BacktestResult:
    strategy_name: str
    strategy_parameters: dict[str, Any]
    metrics: dict[str, float | int]
    equity_curve: pd.DataFrame
    asset_results: pd.DataFrame
    trades: pd.DataFrame

    def summary(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy_name,
            "parameters": self.strategy_parameters,
            "metrics": self.metrics,
            "symbols": sorted(self.asset_results["symbol"].unique().tolist()),
            "start": str(self.equity_curve["timestamp"].min().date()),
            "end": str(self.equity_curve["timestamp"].max().date()),
        }


class Backtester:
    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()
        self.config.validate()

    def run(self, bars: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        clean = self._prepare_bars(bars)
        per_asset: list[pd.DataFrame] = []
        trade_frames: list[pd.DataFrame] = []

        symbols = clean["symbol"].nunique()
        allocation = self.config.initial_capital / symbols

        for symbol, group in clean.groupby("symbol", sort=True):
            asset = group.sort_values("timestamp").copy().reset_index(drop=True)
            target = strategy.generate_signals(asset)
            if len(target) != len(asset):
                raise ValueError("strategy returned a signal series with an invalid length")

            lower_bound = -self.config.max_position_weight if self.config.allow_short else 0.0
            target = target.astype(float).clip(lower_bound, self.config.max_position_weight)
            position = target.shift(1).fillna(0.0)  # execute next bar to avoid look-ahead bias
            market_return = asset["close"].pct_change().fillna(0.0)
            turnover = position.diff().abs().fillna(position.abs())
            costs = turnover * self.config.round_trip_cost_rate
            gross_return = position * market_return
            net_return = gross_return - costs

            asset["target_position"] = target
            asset["position"] = position
            asset["market_return"] = market_return
            asset["gross_return"] = gross_return
            asset["transaction_cost"] = costs
            asset["strategy_return"] = net_return
            asset["asset_equity"] = allocation * (1.0 + net_return).cumprod()
            per_asset.append(asset)
            trade_frames.append(self._extract_trades(asset, allocation))

        asset_results = pd.concat(per_asset, ignore_index=True)
        trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()

        daily = (
            asset_results.groupby("timestamp", as_index=False)
            .agg(
                strategy_return=("strategy_return", "mean"),
                benchmark_return=("market_return", "mean"),
                turnover=("position", lambda s: float(s.diff().abs().sum())),
            )
            .sort_values("timestamp")
        )
        daily["equity"] = self.config.initial_capital * (1.0 + daily["strategy_return"]).cumprod()
        daily["benchmark_equity"] = self.config.initial_capital * (1.0 + daily["benchmark_return"]).cumprod()
        daily["drawdown"] = daily["equity"] / daily["equity"].cummax() - 1.0

        total_turnover = float(asset_results.groupby("symbol")["position"].diff().abs().fillna(0.0).sum())
        metrics = calculate_metrics(
            returns=daily["strategy_return"],
            equity=daily["equity"],
            annualization_factor=self.config.annualization_factor,
            turnover=total_turnover,
            trade_count=len(trades),
        )
        metrics["ending_equity"] = float(daily["equity"].iloc[-1])
        metrics["benchmark_total_return"] = float(daily["benchmark_equity"].iloc[-1] / self.config.initial_capital - 1.0)
        metrics["excess_return"] = float(metrics["total_return"] - metrics["benchmark_total_return"])

        return BacktestResult(
            strategy_name=strategy.name,
            strategy_parameters=strategy.parameters(),
            metrics=metrics,
            equity_curve=daily,
            asset_results=asset_results,
            trades=trades,
        )

    @staticmethod
    def _prepare_bars(bars: pd.DataFrame) -> pd.DataFrame:
        missing = REQUIRED_COLUMNS - set(bars.columns)
        if missing:
            raise ValueError(f"market data is missing columns: {sorted(missing)}")
        if bars.empty:
            raise ValueError("market data cannot be empty")

        clean = bars.copy()
        clean["timestamp"] = pd.to_datetime(clean["timestamp"], utc=True).dt.tz_convert(None)
        clean["symbol"] = clean["symbol"].astype(str).str.upper().str.strip()
        numeric = ["open", "high", "low", "close", "volume"]
        clean[numeric] = clean[numeric].apply(pd.to_numeric, errors="coerce")
        clean = clean.dropna(subset=["timestamp", "symbol", *numeric])
        clean = clean.drop_duplicates(["timestamp", "symbol"], keep="last")
        clean = clean.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

        invalid = (
            (clean["low"] > clean["high"])
            | (clean["open"] <= 0)
            | (clean["high"] <= 0)
            | (clean["low"] <= 0)
            | (clean["close"] <= 0)
            | (clean["volume"] < 0)
        )
        if invalid.any():
            raise ValueError(f"market data contains {int(invalid.sum())} invalid OHLCV rows")
        return clean

    @staticmethod
    def _extract_trades(asset: pd.DataFrame, allocation: float) -> pd.DataFrame:
        change = asset["position"].diff().fillna(asset["position"])
        rows: list[dict[str, object]] = []
        for index in asset.index[change.abs() > 1e-12]:
            delta = float(change.loc[index])
            price = float(asset.loc[index, "close"])
            notional = abs(delta) * allocation
            quantity = notional / price if price > 0 else 0.0
            rows.append(
                {
                    "timestamp": asset.loc[index, "timestamp"],
                    "symbol": asset.loc[index, "symbol"],
                    "side": "BUY" if delta > 0 else "SELL",
                    "quantity": quantity,
                    "price": price,
                    "notional": notional,
                    "position_after": float(asset.loc[index, "position"]),
                }
            )
        return pd.DataFrame(rows)
