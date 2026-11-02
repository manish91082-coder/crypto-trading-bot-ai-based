"""L4 risk rules (Gemini review items #4 anti-liquidation distance and #5 portfolio heat cap; N1 K2 definition).
Pure functions only: no exchange calls, no orders, no settings. NOT wired into any running engine (F6 on the VM is unchanged);
wiring needs the user's explicit approval. Tests: src/audits/test_risk_rules_l4.py.

Liquidation price (isolated margin, one position, simplified Binance USD-M formula without the maintenance amount):
  long : liq = entry * (1 - 1/lev + mmr)      short: liq = entry * (1 + 1/lev - mmr)
The exact Binance formula adds a per-bracket maintenance amount; using mmr only is conservative for small notionals
(it puts the liquidation price slightly closer to the entry)."""
import math

HEAT_CAP = 0.06          # Elder "6% rule" adapted to open stop-risk (N1 K2)
ANTI_LIQ_K = 0.4         # stop distance must be <= 0.4 x liquidation distance (Gemini Spec, kept as a safety margin)


def liquidation_price(entry, side, leverage, mmr):
    assert entry > 0 and leverage >= 1 and 0 <= mmr < 1 and side in (1, -1)
    return entry * (1 - 1 / leverage + mmr) if side == 1 else entry * (1 + 1 / leverage - mmr)


def anti_liq_ok(entry, stop, side, leverage, mmr, k=ANTI_LIQ_K):
    """True if the stop is on the protective side of the entry and its distance <= k x the liquidation distance."""
    if side == 1 and not stop < entry:
        return False
    if side == -1 and not stop > entry:
        return False
    liq = liquidation_price(entry, side, leverage, mmr)
    return abs(stop - entry) <= k * abs(liq - entry) + 1e-12


def max_leverage(entry, stop, side, mmr, k=ANTI_LIQ_K, cap=20):
    """largest integer leverage (1..cap) for which anti_liq_ok holds; 0 if even 1x fails."""
    best = 0
    for lev in range(1, cap + 1):
        if anti_liq_ok(entry, stop, side, lev, mmr, k):
            best = lev
    return best


def stop_risk(notional, entry, stop):
    """loss at the stop as a fraction of nothing: returns notional x |entry - stop| / entry (quote currency)."""
    return notional * abs(entry - stop) / entry


def heat_scale(open_risk, new_risk, equity, cap=HEAT_CAP):
    """scale factor in [0, 1] for a new position so that (open stop-risk + new stop-risk) / equity <= cap (N1 K2 rule)."""
    assert equity > 0 and new_risk >= 0 and open_risk >= 0
    room = cap * equity - open_risk
    if room <= 1e-15 * equity:
        return 0.0
    if new_risk <= room:
        return 1.0
    return room / new_risk


def check_order(entry, stop, side, leverage, mmr, notional, open_risk, equity):
    """combined pre-trade check -> dict(ok, scale, reasons)."""
    reasons = []
    liq_ok = anti_liq_ok(entry, stop, side, leverage, mmr)
    if not liq_ok:
        reasons.append(f"anti-liquidation: stop distance {abs(stop - entry) / entry:.4f} > {ANTI_LIQ_K} x liquidation distance "
                       f"{abs(liquidation_price(entry, side, leverage, mmr) - entry) / entry:.4f} at {leverage}x")
    sc = heat_scale(open_risk, stop_risk(notional, entry, stop), equity)
    if sc < 1.0:
        reasons.append(f"heat cap: scaled to {sc:.3f}")
    return dict(ok=liq_ok and sc > 0, scale=sc if not math.isnan(sc) else 0.0, reasons=reasons)
