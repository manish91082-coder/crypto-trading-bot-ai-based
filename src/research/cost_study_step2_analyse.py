"""
Step 2 cost analysis (protocol: logs/cost_study_step2/STEP2_COST_PROTOCOL_PREREGISTERED.md).
Recomputes every snapshot row from the raw gzip books (SHA256-checked), then the per-fill cost table and the verdict.
Usage: python cost_study_step2_analyse.py [--preliminary]   (--preliminary: allowed before 30 scheduled rounds; labelled)
"""
import sys
import gzip
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "execution"):
    sys.path.insert(0, str(p))
import cost_snapshot_step2 as CS

FEES = dict(fee_0100=0.100, fee_0075=0.075)       # % per fill, Binance VIP 0 (official fee page)
MODEL = 0.25


def main(prelim=False):
    snap = pd.read_csv(CS.LOG / "snapshots.csv")
    # re-derive every row from the raw book
    for f, g in snap.groupby("raw_file"):
        blob = (CS.RAW / f).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == g.raw_sha256.iloc[0], f"{f}: raw hash"
        raw = json.loads(gzip.decompress(blob))
        for r in g.itertuples():
            m = CS.measure(r.symbol, raw[r.symbol]["book"])
            for k in ("half_spread_bps", "buy_bps_333", "sell_bps_333", "buy_bps_10000"):
                a, b = m[k], getattr(r, k)
                assert (np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9, (f, r.symbol, k)
    sched = snap[~snap.off_schedule.astype(bool)]
    n_sched = sched.round_utc.nunique()
    use = sched if n_sched >= 30 else snap
    label = "FINAL" if n_sched >= 30 else "PRELIMINARY"
    assert n_sched >= 30 or prelim, f"only {n_sched} scheduled rounds (< 30); use --preliminary"
    print(f"{label}: {len(snap)} rows re-derived from raw books; scheduled rounds {n_sched}, all rounds {snap.round_utc.nunique()}; "
          f"rows used {len(use)}")
    out = []
    for n in CS.NOTIONALS:
        imp = (use[f"buy_bps_{n}"] + use[f"sell_bps_{n}"]) / 2 / 100            # % per fill (spread + impact)
        per = use.assign(imp=imp).groupby("symbol").imp.median()
        thin = use[f"buy_bps_{n}"].isna().mean()
        row = dict(notional=n, coins=int(per.notna().sum()), thin_share=round(float(thin), 4),
                   impact_median_pct=round(float(per.median()), 4), impact_p90_pct=round(float(per.quantile(0.9)), 4),
                   impact_max_pct=round(float(per.max()), 4), worst_coin=per.idxmax())
        for k, fee in FEES.items():
            med, p90 = fee + per.median(), fee + per.quantile(0.9)
            row[f"{k}_cost_median_pct"], row[f"{k}_cost_p90_pct"] = round(float(med), 4), round(float(p90), 4)
            row[f"{k}_verdict"] = ("0.25% conservative" if p90 <= MODEL else "0.25% too low" if med > MODEL else "borderline")
        out.append(row)
    T = pd.DataFrame(out)
    T.to_csv(CS.LOG / f"cost_table_{label.lower()}.csv", index=False)
    pd.set_option("display.width", 250)
    print(T.to_string(index=False))
    per333 = use.assign(imp=(use.buy_bps_333 + use.sell_bps_333) / 2 / 100).groupby("symbol").imp.median().sort_values()
    per333.round(4).to_csv(CS.LOG / f"per_coin_333_{label.lower()}.csv")
    print("\nper coin, spread+impact at $333 (% per fill):\n", per333.round(4).to_string())


if __name__ == "__main__":
    main(prelim="--preliminary" in sys.argv)
