# M4: changes after the protocol lock

## 1. 2026-10-16: verifier V3 redesigned (E2E integration test finding; collector code unchanged)
- **Problem:** V3 compared the stored Binance options mark IV with a LIVE re-fetch within 5 vol points. Run ~1.5 h after
  the collection it failed on SOL-261030-122-C (stored 0.585, live 0.661): IV really moves within hours, so the check
  tested the market, not the data.
- **New V3:**
  - (a) every closed DVOL hour re-fetched from Deribit history must be EQUAL (history is immutable);
  - (b) every stored Binance futures markPrice must lie inside the 1m mark-price kline of its own minute
    (/fapi/v1/markPriceKlines);
  - (c) the live options IV comparison only when the verifier runs < 15 min after the collection.
- First run of the new V3 on the real ledger: 96 DVOL hours equal; 6 mark prices inside their kline: PASS.
- Verifier SHA: 770731a65ebe6ccbee2fca019bd2eb1da9f93f488c1af0db1a0a731ad0f8e4da  src/audits/verify_m4_collector.py

## 2. 2026-10-16: V3(b) waits until the snapshot minute is closed (E2E sandbox finding)
- Run right after a fresh collection, the 1m mark-price kline of the snapshot minute did not exist yet (empty list ->
  IndexError). V3(b) now waits until that minute has closed, and an empty answer is an explicit failure.
- Verifier SHA: 1cd8239bd6af47ff25f65b2d857bcd295fbad9bb3bcb7840a4fce38523830e00  src/audits/verify_m4_collector.py

## 3. 2026-10-16: V3(c) (live options IV within 5 vol points, < 15 min after collection) removed
- Final E2E run: a fresh sandbox collection, re-fetched within minutes, failed on SOL-261030-122-C (0.625 -> 0.694).
  Short-dated option mark IV jumps within minutes, so the check tested the market, not the stored data.
- Checked alternative: bid IV <= mark IV <= ask IV does NOT hold on Binance (494 of 1,420 quoted options violate it;
  mark IV is model-based), so it cannot be used either.
- **Limitation (stated plainly):** the stored Binance options IV values cannot be independently re-verified later
  (no history endpoint). They are protected by V1 (file SHA256 + ledger chain) and V2 (counts) only. DVOL (Deribit
  history, exact) and futures mark prices (1m mark-price kline) remain independently re-verified by V3(a)(b).
- Verifier SHA: fcb4090377800156953991033859db3d36b6e48b07278b88726d7e408b2baf86  src/audits/verify_m4_collector.py

## 4. 2026-10-17: V3(b) window = the snapshot minute +-1 (cloud VM E2E finding)
- On the cloud VM a fresh sandbox collection failed V3(b): BTCUSDT_261225 markPrice 82280.25 vs the snapshot minute's
  mark kline [82263.42, 82276.09] (about 0.005 % apart). The premiumIndex "time" field does not pin the exact minute
  of the mark price, so the check now uses the high / low of the three 1m mark-price klines minute -1, 0, +1 (it waits
  until minute +1 is closed). The tolerance stays tight (one-minute neighbourhood, no percentage band).
- Verifier SHA: 5362b8f27a32cd53befb36860bdddfbca3bec67686ce237581d08faec967f55f  src/audits/verify_m4_collector.py
