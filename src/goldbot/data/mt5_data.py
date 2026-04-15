"""Compatibility wrapper around AI-first data modules."""

from goldbot.data.indicators import append_indicators
from goldbot.data.mt5_adapter import MT5DataAdapter

__all__ = ["MT5DataAdapter", "append_indicators"]
