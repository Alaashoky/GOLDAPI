"""CLI entrypoint: run, paper, backtest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from goldbot.app.runner import BotRunner
from goldbot.backtest.engine import BacktestEngine
from goldbot.config.settings import load_settings
from goldbot.data.mt5_data import append_indicators
from goldbot.strategies.trend_ema_pullback import TrendEMAPullbackStrategy


def _load_csv_bars(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0].split(",")
    bars = []
    for line in lines[1:]:
        values = line.split(",")
        row = {k: float(v) if k not in {"time"} else v for k, v in zip(header, values)}
        bars.append(row)
    return bars


def main() -> None:
    parser = argparse.ArgumentParser(prog="goldbot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--loop", action="store_true")

    sub.add_parser("paper")

    backtest_cmd = sub.add_parser("backtest")
    backtest_cmd.add_argument("--csv", type=Path, required=True, help="OHLC CSV with columns: time,open,high,low,close")

    args = parser.parse_args()
    settings = load_settings()

    if args.cmd == "paper":
        settings.mode = "paper"
        runner = BotRunner(settings)
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
        bars = append_indicators(
            bars,
            ema_fast=settings.strategy.ema_fast,
            ema_slow=settings.strategy.ema_slow,
            rsi_period=settings.strategy.rsi_period,
            atr_period=settings.strategy.atr_period,
            bb_period=settings.strategy.bb_period,
            bb_std=settings.strategy.bb_std,
        )
        engine = BacktestEngine()
        result = engine.run(bars, TrendEMAPullbackStrategy())
        print(json.dumps(result["metrics"], indent=2))
        return


if __name__ == "__main__":
    main()
