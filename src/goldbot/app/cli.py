"""CLI entrypoint for paper/demo/live/backtest modes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path

from goldbot.app.runner import BotRunner
from goldbot.backtest.engine import BacktestEngine
from goldbot.config.settings import load_settings
from goldbot.data.indicators import append_indicators
from goldbot.data.mt5_adapter import MT5DataAdapter
from goldbot.ops.journal import TradeJournal
from goldbot.strategies.liquidity_sweep import LiquiditySweepStrategy


def _load_csv_bars(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0].split(",")
    numeric_cols = {"open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    bars = []
    for idx, line in enumerate(lines[1:], start=2):
        values = line.split(",")
        try:
            row = {k: float(v) if k.strip().lower() in numeric_cols else v for k, v in zip(header, values)}
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value in CSV at line {idx}: {line}") from exc
        bars.append(row)
    return bars


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _time_to_iso(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="goldbot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--loop", action="store_true")

    paper_cmd = sub.add_parser("paper")
    paper_cmd.add_argument("--loop", action="store_true")

    demo_cmd = sub.add_parser("demo")
    demo_cmd.add_argument("--loop", action="store_true")

    live_cmd = sub.add_parser("live")
    live_cmd.add_argument("--loop", action="store_true")

    backtest_cmd = sub.add_parser("backtest")
    today = datetime.now(tz=timezone.utc).date()
    one_year_ago = today - timedelta(days=365)
    backtest_cmd.add_argument("--csv", type=Path, help="Optional OHLC CSV with columns: time,open,high,low,close")
    backtest_cmd.add_argument("--symbol", default=None, help="MT5 symbol (default from settings)")
    backtest_cmd.add_argument("--timeframe", default="M15", help="MT5 timeframe (default: M15)")
    backtest_cmd.add_argument("--from-date", dest="from_date", default=one_year_ago.isoformat(), help="Start date YYYY-MM-DD")
    backtest_cmd.add_argument("--to-date", dest="to_date", default=today.isoformat(), help="End date YYYY-MM-DD")
    backtest_cmd.add_argument("--entry-model", choices=["next_open", "close"], default="next_open")
    backtest_cmd.add_argument("--spread-points", type=float, default=60.0)
    backtest_cmd.add_argument("--point-value", type=float, default=None)
    backtest_cmd.add_argument("--starting-balance", type=float, default=10000.0)
    backtest_cmd.add_argument("--risk-per-trade-pct", type=float, default=None)
    backtest_cmd.add_argument("--trades-csv", type=Path, default=Path("backtest_trades.csv"))

    args = parser.parse_args()
    settings = load_settings()

    if args.cmd in {"paper", "demo", "live"}:
        settings.mode = args.cmd
        runner = BotRunner(settings)
        if args.loop:
            runner.run_loop()
        else:
            runner.run_once()
        return

    if args.cmd == "run":
        runner = BotRunner(settings)
        if args.loop:
            runner.run_loop()
        else:
            runner.run_once()
        return

    if args.cmd == "backtest":
        symbol = args.symbol or settings.symbol
        if args.csv:
            bars = _load_csv_bars(args.csv)
            point_value = args.point_value if args.point_value is not None else 0.0
            contract_size = 100.0
            volume_min, volume_step, volume_max = 0.01, 0.01, 100.0
        else:
            from_date = _parse_date(args.from_date)
            to_date = _parse_date(args.to_date)
            from_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
            to_dt = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
            adapter = MT5DataAdapter(settings.mt5_login, settings.mt5_password, settings.mt5_server)
            adapter.initialize()
            try:
                adapter.ensure_symbol(symbol)
                bars = adapter.get_rates_range(symbol, args.timeframe.upper(), from_dt, to_dt)
                info = adapter.symbol_info(symbol)
            finally:
                adapter.shutdown()
            inferred_point_value = float(getattr(info, "point", 0.0)) if info is not None else 0.0
            point_value = args.point_value if args.point_value is not None else inferred_point_value
            if point_value <= 0:
                raise ValueError("Point value unavailable from MT5. Please pass --point-value.")
            contract_size = float(getattr(info, "trade_contract_size", 100.0) or 100.0)
            volume_min = float(getattr(info, "volume_min", 0.01) or 0.01)
            volume_step = float(getattr(info, "volume_step", 0.01) or 0.01)
            volume_max = float(getattr(info, "volume_max", 100.0) or 100.0)

        bars = append_indicators(bars)
        engine = BacktestEngine()
        risk_pct = (
            args.risk_per_trade_pct
            if args.risk_per_trade_pct is not None
            else min(settings.risk.risk_per_trade_pct, settings.risk.max_risk_per_trade_pct)
        )
        result = engine.run(
            bars=bars,
            strategy=LiquiditySweepStrategy(),
            starting_balance=args.starting_balance,
            risk_per_trade_pct=risk_pct,
            entry_model=args.entry_model,
            spread_points=args.spread_points,
            point_value=point_value,
            contract_size=contract_size,
            volume_min=volume_min,
            volume_step=volume_step,
            volume_max=volume_max,
        )

        journal = TradeJournal(str(args.trades_csv))
        for trade in result["trades"]:
            journal.record(
                {
                    "timestamp": _time_to_iso(trade.get("exit_time") or trade.get("entry_time")),
                    "strategy": "liquidity_sweep",
                    "regime": "backtest",
                    "signal": trade.get("signal", ""),
                    "entry": trade.get("entry", 0.0),
                    "sl": trade.get("sl", 0.0),
                    "tp": trade.get("tp", 0.0),
                    "lot": trade.get("lot", 0.0),
                    "outcome": trade.get("reason", ""),
                    "pnl": trade.get("pnl", 0.0),
                    "reason": f"R={trade.get('r', 0.0):.2f}",
                }
            )

        metrics = dict(result["metrics"])
        metrics["trades_csv"] = str(args.trades_csv)
        metrics["total_pnl"] = result["total_pnl"]
        metrics["symbol"] = symbol
        metrics["timeframe"] = args.timeframe.upper()
        metrics["from_date"] = args.from_date
        metrics["to_date"] = args.to_date
        metrics["spread_points"] = args.spread_points
        metrics["point_value"] = point_value
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
