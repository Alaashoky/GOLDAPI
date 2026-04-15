"""Position sizing helpers."""

from __future__ import annotations


def calculate_position_size(
    account_balance: float,
    risk_per_trade_pct: float,
    entry_price: float,
    sl_price: float,
    contract_size: float = 100.0,
    volume_min: float = 0.01,
    volume_step: float = 0.01,
    volume_max: float = 100.0,
) -> float:
    if account_balance <= 0 or risk_per_trade_pct <= 0:
        return 0.0
    sl_distance = abs(entry_price - sl_price)
    if sl_distance <= 0:
        return 0.0

    risk_amount = account_balance * (risk_per_trade_pct / 100.0)
    loss_per_lot = sl_distance * contract_size
    if loss_per_lot <= 0:
        return 0.0

    raw_volume = risk_amount / loss_per_lot
    clamped = max(volume_min, min(volume_max, raw_volume))
    steps = int(clamped / volume_step)
    normalized = steps * volume_step
    return round(max(volume_min, normalized), 2)
