from __future__ import annotations

import math

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_peak = equity.cummax()
    drawdown = equity / running_peak - 1.0
    return float(drawdown.min())


def calculate_metrics(
    returns: pd.Series,
    equity: pd.Series,
    annualization_factor: int = 252,
    turnover: float = 0.0,
    trade_count: int = 0,
) -> dict[str, float | int]:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if equity.empty:
        raise ValueError("equity series cannot be empty")

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    periods = max(len(clean), 1)
    years = periods / annualization_factor
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0

    volatility = float(clean.std(ddof=0) * math.sqrt(annualization_factor)) if len(clean) > 1 else 0.0
    annual_return = float(clean.mean() * annualization_factor) if not clean.empty else 0.0
    sharpe = annual_return / volatility if volatility > 0 else 0.0

    downside = clean[clean < 0]
    downside_vol = float(downside.std(ddof=0) * math.sqrt(annualization_factor)) if len(downside) > 1 else 0.0
    sortino = annual_return / downside_vol if downside_vol > 0 else 0.0

    mdd = max_drawdown(equity)
    calmar = cagr / abs(mdd) if mdd < 0 else 0.0
    win_rate = float((clean > 0).mean()) if not clean.empty else 0.0

    gains = float(clean[clean > 0].sum())
    losses = abs(float(clean[clean < 0].sum()))
    profit_factor = gains / losses if losses > 0 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "annualized_return": annual_return,
        "annualized_volatility": volatility,
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "max_drawdown": mdd,
        "calmar_ratio": float(calmar),
        "win_rate": win_rate,
        "profit_factor": float(profit_factor),
        "turnover": float(turnover),
        "trade_count": int(trade_count),
    }
