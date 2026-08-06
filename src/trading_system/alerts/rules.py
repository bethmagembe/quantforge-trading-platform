from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class Alert:
    severity: str
    rule: str
    symbol: str
    message: str
    observed_value: float
    threshold: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_market_alerts(
    bars: pd.DataFrame,
    price_move_threshold: float = 0.05,
    volume_z_threshold: float = 3.0,
    lookback: int = 20,
) -> list[Alert]:
    alerts: list[Alert] = []
    if bars.empty:
        return alerts

    for symbol, group in bars.groupby("symbol"):
        ordered = group.sort_values("timestamp").copy()
        if len(ordered) < 2:
            continue
        ordered["return"] = ordered["close"].pct_change()
        latest = ordered.iloc[-1]
        price_move = float(latest["return"])
        if abs(price_move) >= price_move_threshold:
            alerts.append(
                Alert(
                    severity="high" if abs(price_move) >= price_move_threshold * 1.5 else "medium",
                    rule="large_price_move",
                    symbol=str(symbol),
                    message=f"{symbol} moved {price_move:.2%} in the latest session.",
                    observed_value=price_move,
                    threshold=price_move_threshold,
                )
            )

        volume_window = ordered["volume"].tail(lookback + 1).astype(float)
        historical = volume_window.iloc[:-1]
        if len(historical) >= 5 and historical.std(ddof=0) > 0:
            z_score = float((volume_window.iloc[-1] - historical.mean()) / historical.std(ddof=0))
            if z_score >= volume_z_threshold:
                alerts.append(
                    Alert(
                        severity="medium",
                        rule="volume_spike",
                        symbol=str(symbol),
                        message=f"{symbol} volume is {z_score:.1f} standard deviations above its recent average.",
                        observed_value=z_score,
                        threshold=volume_z_threshold,
                    )
                )
    return alerts


def evaluate_portfolio_alerts(
    equity_curve: pd.DataFrame,
    drawdown_threshold: float = -0.10,
) -> list[Alert]:
    if equity_curve.empty or "drawdown" not in equity_curve:
        return []
    current = float(equity_curve["drawdown"].iloc[-1])
    if current <= drawdown_threshold:
        return [
            Alert(
                severity="high",
                rule="portfolio_drawdown",
                symbol="PORTFOLIO",
                message=f"Portfolio drawdown reached {current:.2%}.",
                observed_value=current,
                threshold=drawdown_threshold,
            )
        ]
    return []
