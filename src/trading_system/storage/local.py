from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_system.engine.backtester import BacktestResult


class LocalArtifactRepository:
    def __init__(self, root: str | Path = "artifacts") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_backtest(self, result: BacktestResult) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.root / f"{result.strategy_name}-{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(
            json.dumps(result.summary(), indent=2, default=str), encoding="utf-8"
        )
        result.equity_curve.to_csv(run_dir / "equity_curve.csv", index=False)
        result.asset_results.to_csv(run_dir / "asset_results.csv", index=False)
        result.trades.to_csv(run_dir / "trades.csv", index=False)
        return run_dir
