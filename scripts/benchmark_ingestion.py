from __future__ import annotations

import argparse
import json

from trading_system.data.benchmark import benchmark_intraday_ingestion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=2_000_000)
    parser.add_argument("--symbols", type=int, default=100)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    args = parser.parse_args()
    result = benchmark_intraday_ingestion(
        rows=args.rows,
        symbols=args.symbols,
        chunk_size=args.chunk_size,
        output_path="artifacts/benchmark_results.json",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
