from __future__ import annotations

from pathlib import Path

import pandas as pd

CANONICAL_COLUMNS = [
    "timestamp",
    "symbol",
    "asset_class",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
]


def load_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = [column.strip().lower() for column in frame.columns]
    if "date" in frame.columns and "timestamp" not in frame.columns:
        frame = frame.rename(columns={"date": "timestamp"})
    if "adj close" in frame.columns and "close" not in frame.columns:
        frame = frame.rename(columns={"adj close": "close"})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["source"] = frame.get("source", "csv")
    frame["asset_class"] = frame.get("asset_class", "unknown")
    return frame


def save_partitioned_csv(frame: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for symbol, group in frame.groupby("symbol"):
        path = root / f"{symbol.replace('/', '_')}.csv"
        group.to_csv(path, index=False)
        paths.append(path)
    return paths


def download_yfinance(symbols: list[str], period: str = "5y") -> pd.DataFrame:
    """Optional live-data adapter. Requires `pip install yfinance` and internet."""
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install the optional yfinance dependency to download public data") from exc

    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        raw = yf.download(symbol, period=period, auto_adjust=False, progress=False)
        if raw.empty:
            continue
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.reset_index().rename(
            columns={
                "Date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        raw["symbol"] = symbol.upper()
        raw["asset_class"] = "unknown"
        raw["source"] = "yfinance"
        frames.append(
            raw[["timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume", "source"]]
        )

    if not frames:
        raise ValueError("No market data was downloaded")
    return pd.concat(frames, ignore_index=True)
