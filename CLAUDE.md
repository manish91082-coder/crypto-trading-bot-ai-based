# Project rules for Claude

- `archive/` holds retired code/data/logs (old pre-rebuild system, rejected steps, unused raw timeframes).
  - NEVER scan, search, read, import or use anything in `archive/` during normal work.
  - Only open it if the user explicitly asks about something archived.
  - Restore notes: `archive/cleanup_2026_10_15/README.md`.
  - EXCEPTION (user, 2026-10-15): the raw multi-timeframe files in `archive/cleanup_2026_10_15/data/raw/`
    (10 coins: 1m (csv + csv.gz), 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1w, 1mo; the 1d files stayed in data/raw) MAY be used whenever a task needs them.
    - Known issue: their 2025+ 1h/15m timestamps are corrupt.
    - Prefer the SHA-verified `data/universe_all` (1d/1h) and `data/universe_hf` (15m/5m). Use the raw files mainly for 1m, or after verifying them.
- No GitHub actions of any kind (no push, PR, issue, or audit on GitHub).
- Reports are written in Hindi.
- Every claim must be backed by verified evidence: pre-registered protocol + SHA lock + independent verifier.
