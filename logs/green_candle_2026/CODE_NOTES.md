2026-10-27 ~06:04 UTC (before the run; run_log start 06:05:18): unit test on synthetic colours R G G D G R G R G G: R1 trades (2->6, 7->8, 9->end forced), R2 (3->6), green runs (1,2),(4,1),(6,1),(8,2) all equal the hand result. Full run started.

Conventions the protocol leaves open (written 2026-10-27 06:1x UTC, while the run was in Part B, before any Part B / Part C number was seen):
1. P2025 is the pool of the six yearly runs (each year is a period run on its own, §6), not one continuous 2020-2025 run. Its random control is the per-seed sum of the yearly random controls.
2. Daily / monthly / yearly attribution: a normal exit is attributed to the open time of the bar whose open is the fill; a forced period-end exit is attributed to the open time of the last bar of the period (so a January forced exit stays in January).
3. Signals need bars inside the period: R1 needs k >= 1, R2 needs k >= 2 (the bar before the period's first bar is not looked at).
4. Bootstrap: one resample set on gross per config; the net CI = gross CI - 2c (cost is a constant per trade, so this is exact).
5. Random-control entry u is uniform over [0, len(P) - bars held), where P = the period's opens plus the last close, so a random trade never leaves the period.
