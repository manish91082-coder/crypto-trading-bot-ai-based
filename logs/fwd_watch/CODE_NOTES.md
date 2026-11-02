# FWD-WATCH code notes (written before any forward number)

- **Code at lock:** `src/forward/fwd_watch.py` SHA 1a39814d78dc5f4365af7916297521d4e7e1145baa9b9b7ec104a9cea2d1295e.
- **Identity selftest on the laptop (2026-10-26 15:25 UTC):**
  - FW1: 81 / 81 bench H trades reproduced exactly;
  - FW2: 938 / 938 NP3 DV trades reproduced exactly.
- **Seed files:** `data/fwd_watch/SEED_MANIFEST.csv` (SHA256 per file).
- **FW1 "closed" rule:**
  - a reversal exit counts when its exit open (bar k + 1) exists;
  - a cap exit counts when t + 2016 ≤ the last bar.
  - Otherwise the trade is open and not counted.
- **FW2 closed rule:** the exit window [t + 4 h, t + 4 h + 15 min) must be in the data. Otherwise the trade is open.
- **Daily table:** closed trades are booked on their exit day.
