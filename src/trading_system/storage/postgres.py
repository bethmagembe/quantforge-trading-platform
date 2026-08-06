from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from trading_system.engine.backtester import BacktestResult


class PostgresRepository:
    """Persists market data and backtest outputs to the PostgreSQL schema in sql/schema.sql."""

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("PostgresRepository requires a PostgreSQL database URL")
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def initialize_schema(self, schema_path: str | Path = "sql/schema.sql") -> None:
        sql = Path(schema_path).read_text(encoding="utf-8")
        statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def ingest_market_bars(self, bars: pd.DataFrame, source: str) -> str:
        run_id = str(uuid.uuid4())
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO ingestion_runs
                        (ingestion_run_id, source, status, rows_received)
                    VALUES (:run_id, :source, 'RUNNING', :rows_received)
                    """
                ),
                {"run_id": run_id, "source": source, "rows_received": len(bars)},
            )
            for symbol, group in bars.groupby("symbol"):
                asset_class = str(group.get("asset_class", pd.Series(["unknown"])).iloc[0])
                connection.execute(
                    text(
                        """
                        INSERT INTO assets(symbol, asset_class)
                        VALUES (:symbol, :asset_class)
                        ON CONFLICT(symbol) DO UPDATE SET asset_class = EXCLUDED.asset_class
                        """
                    ),
                    {"symbol": symbol, "asset_class": asset_class},
                )

            records = bars.to_dict("records")
            for record in records:
                connection.execute(
                    text(
                        """
                        INSERT INTO market_bars(
                            asset_id, bar_time, interval, open, high, low, close,
                            volume, source, ingestion_run_id
                        )
                        SELECT asset_id, :bar_time, '1d', :open, :high, :low, :close,
                               :volume, :source, :run_id
                        FROM assets WHERE symbol = :symbol
                        ON CONFLICT(asset_id, bar_time, interval) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            source = EXCLUDED.source,
                            ingestion_run_id = EXCLUDED.ingestion_run_id
                        """
                    ),
                    {
                        "bar_time": pd.Timestamp(record["timestamp"]).to_pydatetime(),
                        "open": float(record["open"]),
                        "high": float(record["high"]),
                        "low": float(record["low"]),
                        "close": float(record["close"]),
                        "volume": float(record["volume"]),
                        "source": source,
                        "run_id": run_id,
                        "symbol": record["symbol"],
                    },
                )
            connection.execute(
                text(
                    """
                    UPDATE ingestion_runs
                    SET status = 'SUCCEEDED', completed_at = NOW(), rows_inserted = :rows
                    WHERE ingestion_run_id = :run_id
                    """
                ),
                {"rows": len(bars), "run_id": run_id},
            )
        return run_id

    def save_backtest(self, result: BacktestResult, config: dict[str, object]) -> str:
        strategy_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        start = result.equity_curve["timestamp"].min().date()
        end = result.equity_curve["timestamp"].max().date()

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO strategies(strategy_id, name, version, strategy_type, parameters)
                    VALUES (:strategy_id, :name, :version, :strategy_type, CAST(:parameters AS JSONB))
                    ON CONFLICT(name, version) DO UPDATE SET parameters = EXCLUDED.parameters
                    """
                ),
                {
                    "strategy_id": strategy_id,
                    "name": result.strategy_name,
                    "version": "1.0.0",
                    "strategy_type": "rule_based",
                    "parameters": json.dumps(result.strategy_parameters),
                },
            )
            resolved_strategy_id = connection.execute(
                text("SELECT strategy_id FROM strategies WHERE name=:name AND version='1.0.0'"),
                {"name": result.strategy_name},
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO backtest_runs(
                        backtest_run_id, strategy_id, period_start, period_end,
                        initial_capital, commission_bps, slippage_bps, status, completed_at
                    ) VALUES (
                        :run_id, :strategy_id, :period_start, :period_end,
                        :initial_capital, :commission_bps, :slippage_bps, 'SUCCEEDED', NOW()
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "strategy_id": resolved_strategy_id,
                    "period_start": start,
                    "period_end": end,
                    "initial_capital": config["initial_capital"],
                    "commission_bps": config["commission_bps"],
                    "slippage_bps": config["slippage_bps"],
                },
            )
            for name, value in result.metrics.items():
                if isinstance(value, (int, float)):
                    connection.execute(
                        text(
                            """
                            INSERT INTO performance_metrics(backtest_run_id, metric_name, metric_value)
                            VALUES (:run_id, :name, :value)
                            """
                        ),
                        {"run_id": run_id, "name": name, "value": float(value)},
                    )
        return run_id
