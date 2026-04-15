# GOLDAPI - AI-First Gold Trading Bot (Python + MT5)

GOLDAPI is now an **AI-first XAUUSD trading bot**. OpenAI is the decision engine that analyzes multi-timeframe candles, technical indicators, news context, and memory of past trades, then outputs a structured BUY/SELL/HOLD decision.

## Architecture

- `src/goldbot/config`: typed settings + YAML defaults
- `src/goldbot/data`: MT5 adapter, enhanced indicators, multi-timeframe aggregation, Finnhub news feed
- `src/goldbot/ai`: prompts, analyzer, signal validator, SQLite memory
- `src/goldbot/risk`: position sizing + risk guardrails (daily cap, cooldown, max positions, duplicate-block)
- `src/goldbot/execution`: models + MT5 executor (paper/demo/live)
- `src/goldbot/ops`: structured logging, Telegram alerts, journal
- `src/goldbot/backtest`: backtesting engine + metrics
- `src/goldbot/app`: CLI + runner loop

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy and edit env:

```bash
cp .env.example .env
```

Required env vars include:
- `OPENAI_API_KEY`
- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`
- `FINNHUB_API_KEY` (optional; graceful fallback to no-news)

## Run

Paper mode (default):

```bash
PYTHONPATH=src python -m goldbot.app.cli paper
```

Loop mode:

```bash
PYTHONPATH=src python -m goldbot.app.cli run --loop
```

Demo/live:

```bash
PYTHONPATH=src python -m goldbot.app.cli demo --loop
PYTHONPATH=src python -m goldbot.app.cli live --loop
```

## Design Rules

- AI is the decision maker.
- Fail-safe on AI errors: HOLD (no trade).
- Every order must include SL and TP.
- Default mode is paper.
- News and memory degrade gracefully; MT5/OpenAI are critical.

## Testing

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```
