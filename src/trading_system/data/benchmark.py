from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


def benchmark_intraday_ingestion(
    rows: int = 2_000_000,
    symbols: int = 100,
    chunk_size: int = 250_000,
    seed: int = 7,
    output_path: str | Path = "artifacts/benchmark_results.json",
) -> dict[str, float | int]:
    """Generate and aggregate a simulated trading day's intraday records in chunks.

    This validates that the pipeline can process millions of records without
    loading the complete raw dataset into memory at once.
    """
    if rows <= 0 or symbols <= 0 or chunk_size <= 0:
        raise ValueError("rows, symbols, and chunk_size must be positive")

    rng = np.random.default_rng(seed)
    symbol_names = np.array([f"SYM{i:04d}" for i in range(symbols)])
    aggregates: dict[str, dict[str, float]] = {}
    processed = 0
    start = time.perf_counter()

    while processed < rows:
        size = min(chunk_size, rows - processed)
        symbol_ids = rng.integers(0, symbols, size=size)
        prices = 100 * np.exp(rng.normal(0, 0.012, size=size))
        volumes = rng.integers(1, 5_000, size=size)
        seconds = rng.integers(0, 23_400, size=size)
        chunk = pd.DataFrame(
            {
                "symbol": symbol_names[symbol_ids],
                "second": seconds,
                "price": prices,
                "volume": volumes,
            }
        ).sort_values(["symbol", "second"])

        grouped = chunk.groupby("symbol", sort=False).agg(
            open=("price", "first"),
            high=("price", "max"),
            low=("price", "min"),
            close=("price", "last"),
            volume=("volume", "sum"),
            records=("price", "size"),
        )
        for symbol, row in grouped.iterrows():
            current = aggregates.get(symbol)
            if current is None:
                aggregates[symbol] = row.to_dict()
            else:
                current["high"] = max(current["high"], float(row["high"]))
                current["low"] = min(current["low"], float(row["low"]))
                current["close"] = float(row["close"])
                current["volume"] += float(row["volume"])
                current["records"] += float(row["records"])
        processed += size

    elapsed = time.perf_counter() - start
    result: dict[str, float | int] = {
        "rows_processed": processed,
        "symbols": symbols,
        "chunk_size": chunk_size,
        "elapsed_seconds": round(elapsed, 4),
        "rows_per_second": round(processed / elapsed, 2),
        "aggregated_bars": len(aggregates),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
