# F2: code changes after the lock

## 1. Funding settles into the ISOLATED position margin, not the wallet (engine + verifier)
- First run: G0 MAIN long-only reproduced Step 27 exactly (D1 $43,151.15, H4 $49,365.87, H1 $69,134.22). Then the first long-short run stopped on the engine's own assertion `cash >= 0`: the code booked funding to the wallet cash, so a short PAYING funding while all cash was used as margin made cash negative.
- Fact check (three sources): for isolated margin, funding is paid from / credited to that position's isolated margin, which also moves its liquidation price. Sources: Binance support thread reply quoted on r/binance (2024); Pluang isolated-margin guide; BitMEX support article (the same mechanic).
- Fix:
  - funding is added to the position margin;
  - liquidation = the general isolated rule: margin + units*(entry - high) <= 0.005 * units * high. With margin = notional, this equals a price of about entry x 1.990 (the protocol's entry x 1.995 assumed no funding);
  - trade P&L = final position value - fees - initial margin;
  - the verifier was changed to the same rule and now also checks each trade's funding sum.
- No long-short result had been produced before this fix.
- Engine SHA before: 04a3a7789bb120fc773af20c7e3734eff2478dadae6c71fb87f9d983904b01dc
- Engine SHA after: 63834631adb6e4ace14430b34b3df157b3e7631be3f58a5c18ce992f840a41b0
- Verifier SHA after: 3400958f42129f59c1159154a6983738c8d74ac0b01635319f399aa983d7586c
