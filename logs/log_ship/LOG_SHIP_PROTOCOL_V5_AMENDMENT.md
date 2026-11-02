# Log shipping protocol v5 amendment (2026-10-22): the EMO meter and EMO-1 records join the hourly Drive bundle

**Amends:** v1–v4. Everything else is unchanged. Locked before the code change.

**Why.** New systems:
- the EMO meter (`logs/emotion/EMO_METER_PROTOCOL_PREREGISTERED.md`) writes `data/emotion/ledger.jsonl`;
- the EMO-1 download (`EMO1_PROTOCOL_PREREGISTERED.md`) writes a manifest and lists.

**Mirror additions:**
- `logs/emotion`;
- `data/emotion/ledger.jsonl`;
- `data/emotion/emo1_raw/manifest.csv`, `eligible.json`, `symbols.json`.

**Not shipped:** the EMO-1 raw zips. They are public, re-downloadable files, and their SHA256 is in the shipped manifest (same reasoning as the v1 market-cache rule).

**Verifier W4 essential:** add `data/emotion/ledger.jsonl`.

**Test.** T6 copies of the new paths ship with equal md5; T1–T7 unchanged.
