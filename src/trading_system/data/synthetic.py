from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AssetSpec:
    symbol: str
    asset_class: str
    start_price: float
    annual_return: float
    annual_volatility: float
    base_volume: int


DEFAULT_ASSETS = [
    AssetSpec("SPY", "equity_etf", 280.0, 0.09, 0.18, 70_000_000),
    AssetSpec("QQQ", "equity_etf", 170.0, 0.11, 0.24, 45_000_000),
    AssetSpec("GLD", "commodity_etf", 125.0, 0.05, 0.16, 9_000_000),
    AssetSpec("TLT", "bond_etf", 120.0, 0.03, 0.13, 12_000_000),
    AssetSpec("BTC-USD", "crypto", 7_500.0, 0.20, 0.65, 2_000_000),
]


def generate_daily_market_data(
    years: int = 5,
    assets: list[AssetSpec] | None = None,
    seed: int = 42,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Generate deterministic OHLCV data for a fully offline demo.

    The data is synthetic and must not be described as actual market history.
    """
    if years <= 0:
        raise ValueError("years must be positive")

    specs = assets or DEFAULT_ASSETS
    end = pd.Timestamp(end_date or pd.Timestamp.utcnow().date())
    dates = pd.bdate_range(end=end, periods=years * 252)
    rng = np.random.default_rng(seed)
    shared_factor = rng.normal(0.0, 1.0, len(dates))
    frames: list[pd.DataFrame] = []

    for number, spec in enumerate(specs):
        daily_mu = spec.annual_return / 252
        daily_sigma = spec.annual_volatility / np.sqrt(252)
        idiosyncratic = rng.normal(0.0, 1.0, len(dates))
        correlation = 0.35 if spec.asset_class != "crypto" else 0.15
        shock = correlation * shared_factor + np.sqrt(1 - correlation**2) * idiosyncratic
        log_returns = daily_mu - 0.5 * daily_sigma**2 + daily_sigma * shock
        close = spec.start_price * np.exp(np.cumsum(log_returns))

        overnight = rng.normal(0.0, daily_sigma * 0.25, len(dates))
        open_price = close * np.exp(-log_returns + overnight)
        intraday_spread = np.abs(rng.normal(daily_sigma * 0.55, daily_sigma * 0.18, len(dates)))
        high = np.maximum(open_price, close) * (1 + intraday_spread)
        low = np.minimum(open_price, close) * np.maximum(1 - intraday_spread, 0.01)
        volume_noise = rng.lognormal(mean=0.0, sigma=0.35, size=len(dates))
        volume = np.maximum((spec.base_volume * volume_noise).astype(np.int64), 1)

        frames.append(
            pd.DataFrame(
                {
                    "timestamp": dates,
                    "symbol": spec.symbol,
                    "asset_class": spec.asset_class,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "source": "synthetic",
                }
            )
        )

    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "symbol"]).reset_index(drop=True)
