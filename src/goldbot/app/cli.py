"""CLI entrypoint for paper/demo/live/backtest modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from goldbot.app.runner import BotRunner
from goldbot.backtest.engine import BacktestEngine
from goldbot.config.settings import load_settings
from goldbot.data.indicators import append_indicators
from goldbot.strategies.trend_ema_pullback import TrendEMAPullbackStrategy


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
    backtest_cmd.add_argument("--csv", type=Path, required=True, help="OHLC CSV with columns: time,open,high,low,close")

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
        bars = _load_csv_bars(args.csv)
        bars = append_indicators(bars)
        engine = BacktestEngine()
        result = engine.run(bars, TrendEMAPullbackStrategy())
        print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
