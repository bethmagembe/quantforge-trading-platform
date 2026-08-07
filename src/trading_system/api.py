from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from trading_system.config import BacktestConfig
from trading_system.data import generate_daily_market_data
from trading_system.engine import Backtester
from trading_system.strategies import create_strategy

app = FastAPI(title="Trading Research API", version="2.0.0")


class BacktestRequest(BaseModel):
    strategy: Literal["sma_crossover", "rsi_mean_reversion", "momentum", "buy_and_hold"] = "sma_crossover"
    years: int = Field(default=5, ge=1, le=15)
    seed: int = 42
    initial_capital: float = Field(default=100_000, gt=0)
    commission_bps: float = Field(default=2, ge=0, le=100)
    slippage_bps: float = Field(default=1, ge=0, le=100)
    parameters: dict[str, float | int] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/backtests")
def run_backtest(request: BacktestRequest) -> dict[str, object]:
    try:
        bars = generate_daily_market_data(years=request.years, seed=request.seed)
        strategy = create_strategy(request.strategy, **request.parameters)
        config = BacktestConfig(
            initial_capital=request.initial_capital,
            commission_bps=request.commission_bps,
            slippage_bps=request.slippage_bps,
        )
        result = Backtester(config).run(bars, strategy)
        return result.summary()
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
