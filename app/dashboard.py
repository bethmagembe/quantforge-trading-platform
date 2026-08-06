from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from trading_system.alerts import evaluate_market_alerts, evaluate_portfolio_alerts
from trading_system.config import BacktestConfig
from trading_system.data import generate_daily_market_data, load_csv
from trading_system.engine import Backtester
from trading_system.strategies import create_strategy


st.set_page_config(page_title="Portfolio Trading Lab", page_icon="📈", layout="wide")
st.title("📈 Portfolio Trading Lab")
st.caption("Interactive multi-asset backtesting, risk analysis, trade review, and operational alerts.")

with st.sidebar:
    st.header("Experiment setup")
    data_source = st.radio("Data source", ["Offline synthetic demo", "Upload CSV"])
    uploaded = st.file_uploader("Upload OHLCV CSV", type=["csv"], disabled=data_source != "Upload CSV")
    years = st.slider("History (years)", 1, 10, 5, disabled=data_source != "Offline synthetic demo")
    seed = st.number_input("Synthetic seed", min_value=0, value=42, step=1)

    strategy_name = st.selectbox(
        "Strategy",
        ["sma_crossover", "rsi_mean_reversion", "momentum", "buy_and_hold"],
    )
    parameters: dict[str, float | int] = {}
    if strategy_name == "sma_crossover":
        parameters["short_window"] = st.slider("Short moving average", 5, 80, 20)
        parameters["long_window"] = st.slider("Long moving average", 30, 250, 100)
    elif strategy_name == "rsi_mean_reversion":
        parameters["window"] = st.slider("RSI window", 5, 40, 14)
        parameters["oversold"] = st.slider("Oversold threshold", 5, 45, 30)
        parameters["overbought"] = st.slider("Overbought threshold", 55, 95, 70)
    elif strategy_name == "momentum":
        parameters["lookback"] = st.slider("Momentum lookback", 10, 252, 63)
        parameters["threshold"] = st.slider("Return threshold", -0.10, 0.20, 0.00, 0.01)

    initial_capital = st.number_input("Initial capital", min_value=1_000.0, value=100_000.0, step=10_000.0)
    commission_bps = st.slider("Commission (bps)", 0.0, 25.0, 2.0, 0.5)
    slippage_bps = st.slider("Slippage (bps)", 0.0, 25.0, 1.0, 0.5)
    run_clicked = st.button("Run backtest", type="primary", use_container_width=True)


def load_data() -> pd.DataFrame:
    if data_source == "Upload CSV":
        if uploaded is None:
            raise ValueError("Upload a CSV file before running the backtest.")
        frame = pd.read_csv(uploaded)
        temporary = ROOT / "artifacts" / "uploaded_market_data.csv"
        temporary.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(temporary, index=False)
        return load_csv(temporary)
    return generate_daily_market_data(years=years, seed=int(seed))


if run_clicked:
    try:
        bars = load_data()
        strategy = create_strategy(strategy_name, **parameters)
        config = BacktestConfig(
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        result = Backtester(config).run(bars, strategy)
        st.session_state["bars"] = bars
        st.session_state["result"] = result
    except Exception as exc:
        st.error(str(exc))

if "result" not in st.session_state:
    st.info("Configure an experiment in the sidebar, then click **Run backtest**.")
    st.stop()

result = st.session_state["result"]
bars = st.session_state["bars"]
metrics = result.metrics

metric_columns = st.columns(6)
metric_columns[0].metric("Total return", f"{metrics['total_return']:.1%}")
metric_columns[1].metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
metric_columns[2].metric("Max drawdown", f"{metrics['max_drawdown']:.1%}")
metric_columns[3].metric("Volatility", f"{metrics['annualized_volatility']:.1%}")
metric_columns[4].metric("Trades", f"{metrics['trade_count']:,}")
metric_columns[5].metric("Ending equity", f"${metrics['ending_equity']:,.0f}")

performance_tab, trades_tab, risk_tab, alerts_tab, data_tab = st.tabs(
    ["Performance", "Trades", "Risk Lab", "Alerts", "Data Quality"]
)

with performance_tab:
    equity = result.equity_curve.melt(
        id_vars="timestamp",
        value_vars=["equity", "benchmark_equity"],
        var_name="series",
        value_name="value",
    )
    figure = px.line(equity, x="timestamp", y="value", color="series", title="Strategy vs equal-weight benchmark")
    figure.update_layout(yaxis_title="Portfolio value", xaxis_title=None, legend_title=None)
    st.plotly_chart(figure, use_container_width=True)

    monthly = result.equity_curve.set_index("timestamp")["strategy_return"].resample("ME").apply(lambda values: (1 + values).prod() - 1)
    monthly_frame = monthly.to_frame("return")
    monthly_frame["year"] = monthly_frame.index.year
    monthly_frame["month"] = monthly_frame.index.strftime("%b")
    pivot = monthly_frame.pivot(index="year", columns="month", values="return")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivot = pivot.reindex(columns=[month for month in month_order if month in pivot.columns])
    heatmap = px.imshow(pivot, text_auto=".1%", aspect="auto", title="Monthly returns")
    st.plotly_chart(heatmap, use_container_width=True)

with trades_tab:
    if result.trades.empty:
        st.warning("This configuration did not generate any trades.")
    else:
        st.dataframe(result.trades.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "Download trades CSV",
            result.trades.to_csv(index=False),
            file_name="trades.csv",
            mime="text/csv",
        )

with risk_tab:
    drawdown = go.Figure()
    drawdown.add_trace(
        go.Scatter(
            x=result.equity_curve["timestamp"],
            y=result.equity_curve["drawdown"],
            fill="tozeroy",
            name="Drawdown",
        )
    )
    drawdown.update_layout(title="Portfolio drawdown", yaxis_tickformat=".0%", xaxis_title=None)
    st.plotly_chart(drawdown, use_container_width=True)

    st.subheader("Transaction-cost stress test")
    stress_rows = []
    strategy = create_strategy(strategy_name, **parameters)
    for extra_cost in [0, 2, 5, 10, 20]:
        stressed = Backtester(
            BacktestConfig(
                initial_capital=initial_capital,
                commission_bps=commission_bps + extra_cost,
                slippage_bps=slippage_bps,
            )
        ).run(bars, strategy)
        stress_rows.append(
            {
                "extra_cost_bps": extra_cost,
                "total_return": stressed.metrics["total_return"],
                "sharpe_ratio": stressed.metrics["sharpe_ratio"],
                "ending_equity": stressed.metrics["ending_equity"],
            }
        )
    st.dataframe(pd.DataFrame(stress_rows), use_container_width=True, hide_index=True)

with alerts_tab:
    active_alerts = evaluate_market_alerts(bars) + evaluate_portfolio_alerts(result.equity_curve)
    if not active_alerts:
        st.success("No active alerts under the default rules.")
    for alert in active_alerts:
        message = f"**{alert.rule} · {alert.symbol}** — {alert.message}"
        if alert.severity == "high":
            st.error(message)
        else:
            st.warning(message)

with data_tab:
    duplicate_count = int(bars.duplicated(["timestamp", "symbol"]).sum())
    missing_count = int(bars[["open", "high", "low", "close", "volume"]].isna().sum().sum())
    quality_columns = st.columns(4)
    quality_columns[0].metric("Rows", f"{len(bars):,}")
    quality_columns[1].metric("Symbols", bars["symbol"].nunique())
    quality_columns[2].metric("Duplicate keys", duplicate_count)
    quality_columns[3].metric("Missing OHLCV", missing_count)
    st.dataframe(bars.tail(100), use_container_width=True, hide_index=True)
