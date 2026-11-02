"""A1 correction (A0 amendment 2): S-LAD and S-DTB re-generated from REAL-TIME pivots; S-BRK / S-TRD unchanged.
Writes logs/r2_4h_a1/correction/{a1c_trades.parquet, A1c_gate.csv, signal_diff.csv, claims_a1c.json}. Originals are kept."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_sessions as L
import probe_scalein as P
import master_audit_portfolio as MA
import r2_a1_edge_map as A1
import r2_realtime_pivots as RT

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_a1" / "correction"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a0 = ROOT / "logs" / "r2_4h_a0"
    assert sha(a0 / "A0_AMENDMENT_2.md") == (a0 / "A0_AMENDMENT_2_SHA256.txt").read_text().split()[0]
    old = pd.read_parquet(ROOT / "logs" / "r2_4h_a1" / "a1_trades.parquet")
    fund = MA.load_funding(L.COINS)
    rows, diffs = [], []
    for coin in L.COINS:
        bsig, _ = RT.bars4h(coin)
        sig, tl = RT.swing_signals(coin, bsig, P.START, P.END)
        b = P.bars(coin, "4h")
        idx = {t: i for i, t in enumerate(b.index)}
        O, H, Lo, C = (b[k].values.astype("float64") for k in ("open", "high", "low", "close"))
        for name, side, kt, piv, A, failed in sig:
            e = idx.get(pd.Timestamp(kt))
            if e is None or e + A1.T > len(O):
                continue
            stop = piv - P.BUF * A if side == "long" else piv + P.BUF * A
            r = A1.one_trade(O, H, Lo, C, e, side, stop, A)
            if r:
                rows.append(dict(signal=name, coin=coin, side=side, entry_time=b.index[e], sig_i=e - 1, entry_i=e, failed_later=failed, **r))
        print(coin, len(rows), flush=True)
    N = pd.DataFrame(rows)
    first = {c: pd.Timestamp(fund[c][0][0]) for c in fund}
    N["perp_ok"] = [et >= first[c] for et, c in zip(N.entry_time, N.coin)]
    N["funding_R"] = [MA.fund_R(fund, c, s, [(1.0, px, 0)], et, x, A1.TF, R) for c, s, px, et, x, R in
                      zip(N.coin, N.side, N.entry_px, N.entry_time, N.exit_idx, N.R_price)]
    for k, s in A1.COSTS.items():
        N[f"fee_{k}"] = s * (N.entry_px + N.exit_px) / N.R_price
        N[f"net_{k}"] = N.gross - N[f"fee_{k}"] - N.funding_R
    N["year"] = N.entry_time.dt.year
    N["period"] = np.where(N.entry_time < A1.P1_END, "P1", np.where(N.entry_time < A1.DEV_END, "P2", "P3"))
    # diff vs the original A1 swing signals
    key = ["signal", "coin", "side", "entry_time"]
    o = old[old.signal.isin(["S-LAD", "S-DTB"])]
    m = N.merge(o[key + ["gross"]], on=key, how="outer", suffixes=("", "_old"), indicator=True)
    m["kind"] = np.where(m._merge == "both", "same", np.where(m._merge == "left_only", "new_realtime", "old_only"))
    m[key + ["kind", "failed_later", "gross", "gross_old"]].to_csv(OUT / "signal_diff.csv", index=False)
    same_gross = float(np.nanmax(np.abs(m.loc[m.kind == "same", "gross"] - m.loc[m.kind == "same", "gross_old"])))
    new = m[m.kind == "new_realtime"]
    check = dict(n_same=int((m.kind == "same").sum()), n_new=int(len(new)), n_old_only=int((m.kind == "old_only").sum()),
                 new_all_failed_pivots=bool(new.failed_later.fillna(False).astype(bool).all()),
                 same_all_nonfailed=bool((~m.loc[m.kind == "same", "failed_later"].astype(bool)).all()),
                 max_gross_diff_same=same_gross)
    full = pd.concat([old[old.signal.isin(["S-BRK", "S-TRD"])], N.drop(columns=["failed_later"])], ignore_index=True)
    full = full.merge(N[key + ["failed_later"]], on=key, how="left")
    full["failed_later"] = full.failed_later.fillna(False).astype(bool)
    full.to_parquet(OUT / "a1c_trades.parquet", index=False)
    G = A1.gate(full)
    G.to_csv(OUT / "A1c_gate.csv", index=False)
    Gold = pd.read_csv(ROOT / "logs" / "r2_4h_a1" / "A1_gate.csv")
    cmp_ = G[["signal", "side", "n_dev", "mean_net", "ci_lo", "ci_hi", "net_P1", "net_P2", "net_P3", "gross_over_cost", "PASS"]].merge(
        Gold[["signal", "side", "n_dev", "mean_net", "ci_lo", "PASS"]], on=["signal", "side"], suffixes=("", "_orig"))
    cmp_.to_csv(OUT / "A1c_vs_A1.csv", index=False)
    claims = dict(amend2_sha=sha(a0 / "A0_AMENDMENT_2.md"), trades_sha=sha(OUT / "a1c_trades.parquet"), check=check,
                  gate={f"{r.signal}|{r.side}": dict(PASS=bool(r.PASS), mean_net=float(r.mean_net), ci_lo=float(r.ci_lo)) for r in G.itertuples()})
    (OUT / "claims_a1c.json").write_text(json.dumps(claims, indent=1))
    print(json.dumps(check, indent=1))
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(cmp_.round(4).to_string())
        print(new[key + ["gross"]].assign(gross=new.gross.round(3)).groupby(["signal", "side"]).gross.describe().round(3).to_string())


if __name__ == "__main__":
    main()
