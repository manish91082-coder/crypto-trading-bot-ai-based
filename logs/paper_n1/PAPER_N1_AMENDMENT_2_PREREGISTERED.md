# PAPER-N1 amendment 2 (2026-10-24): delisted and delisting coins (no signal change for listed coins)

**Amends:** `PAPER_N1_PROTOCOL_PREREGISTERED.md` and amendment 1.

**Source:**
- The log audit of 2026-10-23: `/fapi/v1/klines SXPUSDT: HTTP Error 400` in 17 of 19 cycles.
- A listing check on 2026-10-24: 29 of the 133 universe coins have spot not TRADING or the perp settled or missing.

**Lock and approval.** Locked before the code change. The user approved the work on 2026-10-24.

**Scope.**
- Signals, sleeves, weights, venues, fees, the safety rules and the universe list in `deploy/paper_n1_config.json` are unchanged.
- Only coins that the exchange reports as not trading (or with a delisting date announced) are handled.

## Rule (same idea as ECO amendment 2: deliveryDate < 2100 → out)

1. **Daily listing check.**
   - Once per UTC day, at the first cycle of that day, the live run reads the public spot `/api/v3/exchangeInfo` and the futures `/fapi/v1/exchangeInfo`.
   - The universe for the check is CORE10 ∪ U2X ∪ the held coins.
   - **inactive:** spot status ≠ TRADING, or the symbol is missing. Spot is the price and signal source.
   - **perp_out:** not inactive, the coin has a perp mapping, and the perp is missing, or its status ≠ TRADING, or its deliveryDate < 2100-01-01 (4102444800000 ms).
2. **inactive coins.**
   - They are not requested and get no new opens.
   - A held position is closed in that cycle at its last mark price (`last_px`; no spot price exists), with reason `delist` and a note.
3. **perp_out coins.**
   - They get no new opens in any sleeve.
   - A held **perp-venue** position is closed at the cycle's spot open (or its last mark if that is missing), with reason `delist`.
   - A held **spot-venue** position (A/B routing) is kept and exits by its signal as before.
4. **Failure.**
   - If either exchangeInfo call fails, the previous day's lists are kept and a note is written.
   - If no list exists yet, nothing is excluded that cycle.
5. **Record.**
   - Every ledger record gets `delisting` = {day, inactive, perp_out} (or `"off"` in replay).
   - The lists are kept in the state under `delist`.
6. **Replay.**
   - The rule is off in `--replay` (no historical exchangeInfo exists).
   - So replays are unchanged, and that is how "no signal change" is checked.

## Checks (before the cloud update)

- **C1 replay** 2025-06-01 … 2025-08-01, amendment 1 code vs amendment 2 code on the same data: identical ledger actions and equity.
- **C2 unit checks** (no network):
  - (a) an inactive held coin is not requested, is closed at its last mark and is noted;
  - (b) a perp_out coin gets no new open; its perp position is closed at the open and its spot position is kept;
  - (c) an exchangeInfo failure keeps the previous lists;
  - (d) the lists are fetched once per UTC day (a catch-up of several cycles on one day fetches once).
- **C3 VM sandbox cycle** on a copy of the live state, in a scratch root (not `data/paper_n1`):
  - `data_errors` is empty or contains no SXP;
  - the lists match an independent exchangeInfo read;
  - the 301 held positions are unaffected (none is in the lists).
- **C4** `verify_paper_live.py` passes after deploy: the new code SHA is listed in `logs/paper_n1/CODE_CHANGES_AFTER_LOCK.md`. Then the first live cycle is checked.
