from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_system.alerts import evaluate_market_alerts, evaluate_portfolio_alerts
from trading_system.config import BacktestConfig
from trading_system.data import generate_daily_market_data, load_csv
from trading_system.data.benchmark import benchmark_intraday_ingestion
from trading_system.engine import Backtester
from trading_system.reporting import generate_eod_report
from trading_system.storage import LocalArtifactRepository
from trading_system.strategies import create_strategy


def _strategy_params(args: argparse.Namespace) -> dict[str, object]:
    if args.strategy == "sma_crossover":
        return {"short_window": args.short_window, "long_window": args.long_window}
    if args.strategy == "rsi_mean_reversion":
        return {"window": args.rsi_window, "oversold": args.oversold, "overbought": args.overbought}
    if args.strategy == "momentum":
        return {"lookback": args.lookback, "threshold": args.threshold}
    return {}


def run_backtest(args: argparse.Namespace) -> None:
    bars = load_csv(args.data) if args.data else generate_daily_market_data(years=args.years, seed=args.seed)
    strategy = create_strategy(args.strategy, **_strategy_params(args))
    config = BacktestConfig(
        initial_capital=args.initial_capital,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        allow_short=args.allow_short,
    )
    result = Backtester(config).run(bars, strategy)
    run_dir = LocalArtifactRepository(args.output).save_backtest(result)
    alerts = evaluate_market_alerts(bars) + evaluate_portfolio_alerts(result.equity_curve)
    html_path, json_path = generate_eod_report(result, alerts, run_dir / "eod")
    print(json.dumps(result.summary(), indent=2, default=str))
    print(f"Artifacts: {run_dir}")
    print(f"EOD report: {html_path}")
    print(f"JSON report: {json_path}")


def generate_data(args: argparse.Namespace) -> None:
    frame = generate_daily_market_data(years=args.years, seed=args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    print(f"Wrote {len(frame):,} synthetic daily bars to {path}")


def run_benchmark(args: argparse.Namespace) -> None:
    result = benchmark_intraday_ingestion(
        rows=args.rows,
        symbols=args.symbols,
        chunk_size=args.chunk_size,
        output_path=args.output,
    )
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-system", description="Multi-asset trading research platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    data_parser = subparsers.add_parser("generate-data", help="Create an offline five-year synthetic dataset")
    data_parser.add_argument("--years", type=int, default=5)
    data_parser.add_argument("--seed", type=int, default=42)
    data_parser.add_argument("--output", default="data/sample/market_data.csv")
    data_parser.set_defaults(func=generate_data)

    backtest = subparsers.add_parser("backtest", help="Run a strategy and produce reports")
    backtest.add_argument("--data", help="CSV path; omit to use synthetic data")
    backtest.add_argument("--years", type=int, default=5)
    backtest.add_argument("--seed", type=int, default=42)
    backtest.add_argument(
        "--strategy",
        choices=["sma_crossover", "rsi_mean_reversion", "momentum", "buy_and_hold"],
        default="sma_crossover",
    )
    backtest.add_argument("--short-window", type=int, default=20)
    backtest.add_argument("--long-window", type=int, default=100)
    backtest.add_argument("--rsi-window", type=int, default=14)
    backtest.add_argument("--oversold", type=float, default=30)
    backtest.add_argument("--overbought", type=float, default=70)
    backtest.add_argument("--lookback", type=int, default=63)
    backtest.add_argument("--threshold", type=float, default=0)
    backtest.add_argument("--initial-capital", type=float, default=100_000)
    backtest.add_argument("--commission-bps", type=float, default=2)
    backtest.add_argument("--slippage-bps", type=float, default=1)
    backtest.add_argument("--allow-short", action="store_true")
    backtest.add_argument("--output", default="artifacts")
    backtest.set_defaults(func=run_backtest)

    benchmark = subparsers.add_parser("benchmark", help="Process millions of simulated intraday records")
    benchmark.add_argument("--rows", type=int, default=2_000_000)
    benchmark.add_argument("--symbols", type=int, default=100)
    benchmark.add_argument("--chunk-size", type=int, default=250_000)
    benchmark.add_argument("--output", default="artifacts/benchmark_results.json")
    benchmark.set_defaults(func=run_benchmark)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
