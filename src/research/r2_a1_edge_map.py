"""A1: rule-signal edge map on 4h, no AI. Protocol logs/r2_4h_a1/A1_PROTOCOL_PREREGISTERED.md (sub-protocol of A0).

Historical simulation only. Reuses the verified S6 engine (probe_scalein.bars / simulate / signals) and the verified
real-funding routine of the master audit (master_audit_portfolio.load_funding / fund_R).
"""
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

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_a1"
TF, T = "4h", P.T
COSTS = dict(base=0.00054, x1_5=0.00081, x2=0.00108, optimistic=0.00045, no_bnb=0.00059)
DEV_END, P1_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2024-01-01")
SEED, NBOOT = 20261019, 2000


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def atr14(b):
    pc = b.close.shift(1)
    tr = pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().values


def dtb_signals(legs, coin):
    g = legs[(legs.coin == coin) & (legs.tf == TF) & (legs.K == 3.0)].sort_values("start_time")
    pt = L.points(g)
    pt["atr_next"] = np.append(g.atr_confirm.values[1:], np.nan)
    out = []
    for typ, lab, side in (("L", "HL", "long"), ("H", "LH", "short")):
        ii = np.where(pt.typ.values == typ)[0]
        for a, b in zip(ii[:-1], ii[1:]):
            x = pt.iloc[b]
            if abs(x.price - pt.price.iloc[a]) <= 0.5 * x.atr_start and x.label == lab:
                out.append((side, x.known_time, x.price, x.atr_next))
    return [s for s in out if pd.notna(s[1]) and P.START <= s[1] < P.END and np.isfinite(s[3]) and s[3] > 0]


def bar_signals(b, kind):
    """(signal bar i, side) for S-BRK / S-TRD; entry is bar i+1."""
    c, h, l = b.close.values, b.high.values, b.low.values
    out = []
    if kind == "S-BRK":
        hh = pd.Series(h).shift(1).rolling(20).max().values
        ll = pd.Series(l).shift(1).rolling(20).min().values
        for i in range(len(c)):
            if np.isfinite(hh[i]) and c[i] > hh[i]:
                out.append((i, "long"))
            elif np.isfinite(ll[i]) and c[i] < ll[i]:
                out.append((i, "short"))
    else:
        ema = pd.Series(c).ewm(alpha=2 / 51, adjust=False).mean().values
        for i in range(6, len(c)):
            if c[i - 1] <= ema[i - 1] and c[i] > ema[i] and ema[i] > ema[i - 6]:
                out.append((i, "long"))
            elif c[i - 1] >= ema[i - 1] and c[i] < ema[i] and ema[i] < ema[i - 6]:
                out.append((i, "short"))
    return out


def one_trade(O, H, Lo, C, e, side, stop_px, A):
    s = slice(e, e + T)
    if side == "long":
        o, h, l, c, stop0 = O[s], H[s], Lo[s], C[s], stop_px
    else:
        o, h, l, c, stop0 = -O[s], -Lo[s], -H[s], -C[s], -stop_px
    R = o[0] - stop0
    if not R > 0:
        return None
    res, ex_px, ex_i = P.simulate(o, h, l, c, stop0, A, P.HOURS[TF])
    gross = (ex_px - o[0]) / R
    return dict(R_price=R, atr=A, entry_px=abs(o[0]), exit_px=abs(ex_px), exit_idx=ex_i, gross=gross)


def run():
    legs = pd.read_parquet(L.LEGS, columns=["coin", "tf", "K", "direction", "start_time", "start_price", "end_time", "end_price",
                                            "end_i", "confirm_time", "atr_start", "atr_confirm", "move_atr"])
    fund = MA.load_funding(L.COINS)
    rows = []
    for coin in L.COINS:
        b = P.bars(coin, TF)
        idx = {t: i for i, t in enumerate(b.index)}
        O, H, Lo, C = (b[k].values.astype("float64") for k in ("open", "high", "low", "close"))
        atr = atr14(b)
        # swing-point signals (no one-open rule: as S6)
        for sig, lst in (("S-LAD", P.signals(legs, coin, TF)), ("S-DTB", dtb_signals(legs, coin))):
            for side, kt, piv, A in lst:
                e = idx.get(pd.Timestamp(kt))
                if e is None or e + T > len(O):
                    continue
                stop = piv - P.BUF * A if side == "long" else piv + P.BUF * A
                r = one_trade(O, H, Lo, C, e, side, stop, A)
                if r:
                    rows.append(dict(signal=sig, coin=coin, side=side, entry_time=b.index[e], sig_i=e - 1, entry_i=e, **r))
        # bar signals with the one-open rule
        for sig in ("S-BRK", "S-TRD"):
            busy = {"long": -1, "short": -1}
            for i, side in bar_signals(b, sig):
                e = i + 1
                if i <= busy[side] or e + T > len(O) or not np.isfinite(atr[i]) or not (P.START <= b.index[e] < P.END):
                    continue
                A = atr[i]
                stop = O[e] - 2 * A if side == "long" else O[e] + 2 * A
                r = one_trade(O, H, Lo, C, e, side, stop, A)
                if r:
                    rows.append(dict(signal=sig, coin=coin, side=side, entry_time=b.index[e], sig_i=i, entry_i=e, **r))
                    busy[side] = e + r["exit_idx"]
        print(f"{coin}: {len(rows)} trades so far", flush=True)
    D = pd.DataFrame(rows)
    first = {c: pd.Timestamp(fund[c][0][0]) for c in fund}
    D["perp_ok"] = [et >= first[c] for et, c in zip(D.entry_time, D.coin)]
    D["funding_R"] = [MA.fund_R(fund, c, s, [(1.0, px, 0)], et, x, TF, R) for c, s, px, et, x, R in
                      zip(D.coin, D.side, D.entry_px, D.entry_time, D.exit_idx, D.R_price)]
    for k, s in COSTS.items():
        D[f"fee_{k}"] = s * (D.entry_px + D.exit_px) / D.R_price
        D[f"net_{k}"] = D.gross - D[f"fee_{k}"] - D.funding_R
    D["year"] = D.entry_time.dt.year
    D["period"] = np.where(D.entry_time < P1_END, "P1", np.where(D.entry_time < DEV_END, "P2", "P3"))
    return D


def boot_ci(g, col, rng):
    blocks = [gb[col].values for _, gb in g.groupby(["coin", "year"])]
    s = np.array([x.sum() for x in blocks]); n = np.array([len(x) for x in blocks])
    pick = rng.integers(0, len(blocks), (NBOOT, len(blocks)))
    bs = s[pick].sum(1) / n[pick].sum(1)
    return np.percentile(bs, [2.5, 97.5])


def gate(D):
    rng = np.random.default_rng(SEED)
    out = []
    for (sig, side), g in D[D.perp_ok].groupby(["signal", "side"]):
        dev = g[g.period != "P3"]
        lo, hi = boot_ci(dev, "net_base", rng)
        cost = dev.fee_base.mean() + max(dev.funding_R.mean(), 0.0)
        r = dict(signal=sig, side=side, n_dev=len(dev), n_P3=int((g.period == "P3").sum()),
                 mean_gross=dev.gross.mean(), mean_fee=dev.fee_base.mean(), mean_funding=dev.funding_R.mean(),
                 gross_over_cost=dev.gross.mean() / cost, mean_net=dev.net_base.mean(), median_net=dev.net_base.median(),
                 p05_net=np.percentile(dev.net_base, 5), win_rate=(dev.net_base > 0).mean(), ci_lo=lo, ci_hi=hi,
                 net_P1=g[g.period == "P1"].net_base.mean(), net_P2=g[g.period == "P2"].net_base.mean(),
                 net_P3=g[g.period == "P3"].net_base.mean(), trades_per_year_dev=len(dev) / ((DEV_END - P.START).days / 365.25))
        for k in COSTS:
            r[f"net_dev_{k}"] = dev[f"net_{k}"].mean()
        r["PASS"] = bool(dev.gross.mean() >= 2 * cost and r["net_P1"] > 0 and r["net_P2"] > 0)
        out.append(r)
    return pd.DataFrame(out)


def main():
    proto = OUT / "A1_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "A1_PROTOCOL_SHA256.txt").read_text().split()[0], "A1 protocol changed after lock"
    a0 = ROOT / "logs" / "r2_4h_a0" / "A0_4H_PROTOCOL_PREREGISTERED.md"
    assert sha(a0) == (a0.parent / "A0_PROTOCOL_SHA256.txt").read_text().split()[0], "A0 changed after lock"
    assert sha(L.LEGS) == L.LEGS_SHA
    D = run()
    D.to_parquet(OUT / "a1_trades.parquet", index=False)
    G = gate(D)
    G.to_csv(OUT / "A1_gate.csv", index=False)
    claims = dict(a1_protocol_sha=sha(proto), a0_sha=sha(a0), legs_sha=sha(L.LEGS), trades_sha=sha(OUT / "a1_trades.parquet"),
                  gate={f"{r.signal}|{r.side}": dict(PASS=bool(r.PASS), mean_net=float(r.mean_net), gross_over_cost=float(r.gross_over_cost))
                        for r in G.itertuples()},
                  n_excluded_no_perp=int((~D.perp_ok).sum()))
    (OUT / "claims_a1.json").write_text(json.dumps(claims, indent=1))
    log = [f"A1 protocol {claims['a1_protocol_sha']}", f"A0 {claims['a0_sha']}", f"trades {len(D)} (no-perp excluded {claims['n_excluded_no_perp']})"]
    (OUT / "run_log.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(G.round(4).to_string())


if __name__ == "__main__":
    main()
