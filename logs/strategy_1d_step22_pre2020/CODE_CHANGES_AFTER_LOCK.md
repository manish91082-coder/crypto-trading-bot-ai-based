# Step 22: changes after the lock (2026-10-14T10:59:45Z)

## 1. Data FORMAT fix of 5 hourly files (no code change, no value change)
- **Symptom:** the first run crashed in `step9.hourly_daily_features` (`.dt accessor with datetimelike values`). The crash came while building the 2017-19 features, BEFORE any 2017-19 prediction, label, AUC or portfolio was computed. The only 2017-19 output seen was the list of reference coins present.
- **Cause (real Binance data):** after the 8–9 Feb 2018 Binance outage, 43 hourly candles of BTC, ETH, BNB, LTC and NEO open off the hour (e.g. 2018-02-09 09:28:14.789, from Binance's own files).
  - pandas `to_csv` (in the downloader) wrote the 10,000-row chunk that contains them with milliseconds and the later chunks without.
  - `read_csv(parse_dates=...)` then cannot parse the mixed formats.
- **Fix:** text-level only. Timestamps without a fraction got the suffix ".000". Every other character of every line is asserted identical, and the parsed timestamps are asserted identical to the original values.
- **Why the first attempt was rejected:** a pandas re-serialisation changed one float, BTC `quote_volume` 224345659.93453932 → 224345659.9345393, a 1-ulp parse difference. That attempt was reverted from the backup.
- **Originals:** kept in `data/universe_pre2020/1h_original_mixed_format/`.
- **SHA256 before and after:** `logs/universe_pre2020_download/timestamp_format_fix.csv`.
- **Impact:** the off-hour candles stay as Binance published them. Days whose hourly aggregate does not match the 1d candle get NaN 1h features, which is the existing Step 9 cross-check rule.

## 2. 2026-10-15: verifier reads the forward ledger with `forward_dryrun_1d.read_ledger`
- **Why:** the ledger now mixes 19- and 20-field lines (see Step 16 change 3), and `pd.read_csv` failed.
- **Effect:** the logic is unchanged. The verifier still checks that the frozen model SHA equals the ledger SHA. A re-run gives V1–V5 PASS.
