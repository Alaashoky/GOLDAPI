# GOLDAPI - Gold Trading Bot (Python + MT5)

Production-oriented XAUUSD bot with modular architecture, strategy portfolio, AI filtering, risk guardrails, backtesting, and journaling.

## Architecture

- `src/goldbot/config`: typed settings + defaults
- `src/goldbot/data`: MT5 data adapter + indicator calculations + news filter interface
- `src/goldbot/strategies`: EMA pullback, breakout, ATR expansion, RSI+BB mean reversion, regime selector
- `src/goldbot/risk`: position sizing + guardrails (daily loss cap, max open trades, cooldown, duplicate-block)
- `src/goldbot/ai`: OpenAI structured approve/reject filter (timeout/retry, fail-safe)
- `src/goldbot/execution`: order models + MT5 execution wrapper (paper/demo/live-safe)
- `src/goldbot/backtest`: simple event backtest + metrics
- `src/goldbot/ops`: structured logging, optional Telegram alerts, CSV/SQLite journal
- `src/goldbot/app`: runner and CLI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `.env` values (especially MT5/OpenAI keys).

## Run

### Paper mode (safe default)
```bash
PYTHONPATH=src python -m goldbot.app.cli paper
```

### Run once (current mode from env)
```bash
PYTHONPATH=src python -m goldbot.app.cli run
```

### Loop mode
```bash
PYTHONPATH=src python -m goldbot.app.cli run --loop
```

### Backtest sample
```bash
PYTHONPATH=src python -m goldbot.app.cli backtest --csv /absolute/path/to/xauusd_ohlc.csv
```

CSV columns: `time,open,high,low,close`.

## Safety notes

- Default mode is `paper`.
- AI failures/timeouts are fail-safe (`REJECT` by default).
- Every order enforces SL/TP.
- Demo-first is strongly recommended before any live use.
- Live mode is high risk; use strict risk settings and only funds you can afford to lose.

## Testing

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```
