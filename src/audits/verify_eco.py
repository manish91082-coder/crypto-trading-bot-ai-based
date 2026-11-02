"""Independent verifier for ECO (logs/eco/ECO_PROTOCOL_PREREGISTERED.md §9). Own code: does NOT import src/eco or src/research.
V1 E-1: Calmar / CAGR / MTM-DD of the saved N1 FINAL hourly curves (N6 windows) == N6 claims (T19 S2)
V2 E-2: own combination + inverse-vol + stats + acceptance + selection + DSR + kill K from the two raw series
V3 replay targets: 200 random cycles, component targets recomputed from the replay producer files with own fraction code
V4 replay R1 attribution identity and R2 tracking, R3 caps, R5 minimums, R6 determinism (two ledgers)
V5 SHAs: protocol lock, claims files, ECO registry chain
Usage: python verify_eco.py [e2] [replay <dir1> <dir2>]"""
import base64
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "eco"
DER = R_ / "data" / "derived" / "eco"
E0 = 10_000.0
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def st_(v, t0, t1):
    yrs = (pd.Timestamp(t1) - pd.Timestamp(t0)).days / 365.25
    x = np.r_[E0, v.values]
    dd = float((1 - x / np.maximum.accumulate(x)).max())
    cagr = (float(v.iloc[-1]) / E0) ** (1 / yrs) - 1
    me = v.groupby(v.index.to_period("M")).last()
    return cagr, dd, cagr / dd, me / me.shift(1).fillna(E0) - 1


def v_e2():
    cl = json.loads((O_ / "claims_eco_e2.json").read_text())
    n6 = pd.read_csv(R_ / "logs" / "research_n6_safety_sizing" / "N6_results.csv")
    W6 = {"dev": ("2020-02-01", "2025-10-01"), "P1": ("2020-02-01", "2024-01-01"), "P2": ("2024-01-01", "2025-10-01"), "P3": ("2025-10-01", "2026-10-01")}
    md = 0.0
    for wn, (t0, t1) in W6.items():
        c = pd.read_parquet(DER / f"n1_final_hourly_N6win_{wn}.parquet").equity
        cagr, dd, cal, _ = st_(c, t0, t1)
        ref = n6[(n6.trial == "T19") & (n6.variant == "S2") & (n6.window == wn)].iloc[0]
        md = max(md, abs(cal - ref.calmar), abs(dd - ref.mtm_dd), abs(cagr - ref.cagr))
    ok("V1", md < 1e-9 and cl["e1_pass"], f"N1 FINAL curves reproduce N6 T19-S2 (Calmar, DD, CAGR) in 4 windows: max |diff| {md:.1e}")
    # V2
    W = {"dev": ("2021-01-01", "2025-10-01"), "P1": ("2021-01-01", "2024-01-01"), "P2": ("2024-01-01", "2025-10-01"), "P3": ("2025-10-01", "2026-10-01")}
    rs = pd.read_csv(R_ / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date").M_AI3
    r1_all = rs.pct_change()
    nret = []
    for k in ("dev", "P3"):
        c = pd.read_parquet(DER / f"n1_final_hourly_{k}.parquet").equity
        d = c.groupby(c.index.normalize()).last()
        nret.append(d / np.r_[E0, d.values[:-1]] - 1)
    rn_all = pd.concat(nret).sort_index()
    out, mon = {}, {}
    for wn, (t0, t1) in W.items():
        days = pd.date_range(t0, pd.Timestamp(t1) - pd.Timedelta(days=1))
        c = pd.read_parquet(DER / f"n1_final_hourly_{wn}.parquet").equity
        n1 = c.groupby(c.index.normalize()).last().reindex(days)
        rn = n1 / np.r_[E0, n1.values[:-1]] - 1
        b = E0 if days[0] == rs.index[0] else rs.loc[days[0] - pd.Timedelta(days=1)]
        v1 = rs.reindex(days)
        r1 = v1 / np.r_[b, v1.values[:-1]] - 1

        def a_inv(d):
            p1 = r1_all[r1_all.index < d].dropna().tail(126); pn = rn_all[rn_all.index < d].dropna().tail(126)
            if len(p1) < 126 or len(pn) < 126:
                return 0.5
            return float(np.clip((1 / p1.std()) / (1 / p1.std() + 1 / pn.std()), 0.2, 0.8))
        for name, f in (("ECO-W1", lambda d: 0.5), ("ECO-W2", a_inv)):
            E, Em, cm, vals, a = E0, E0, None, [], 0.5
            for d in days:
                if d.to_period("M") != cm:
                    cm, Em, a = d.to_period("M"), E, f(d)
                E += Em * (a * r1[d] + (1 - a) * rn[d])
                vals.append(E)
            cagr, dd, cal, mret = st_(pd.Series(vals, index=days), t0, t1)
            out[(wn, name)] = (cal, dd); mon[(wn, name)] = mret
        cagr, dd, cal, mret = st_(n1, t0, t1)
        out[(wn, "N1_alone")] = (cal, dd); mon[(wn, "N1_alone")] = mret
    R = pd.read_csv(O_ / "E2_results.csv")
    mx = max(abs(R[(R.window == w) & (R.config == c)].calmar.iloc[0] - out[(w, c)][0]) for (w, c) in out)
    srs = [mon[("dev", c)] for c in ("ECO-W1", "ECO-W2", "N1_alone")]
    sv = np.var([s.mean() / s.std() for s in srs], ddof=1)
    acc = {}
    for c in ("ECO-W1", "ECO-W2"):
        r = mon[("dev", c)]
        sr = r.mean() / r.std(); g = 0.5772156649; n = 27
        sr0 = np.sqrt(sv) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
        p = norm.cdf((sr - sr0) * np.sqrt(len(r) - 1) / np.sqrt(1 - r.skew() * sr + (r.kurt() + 2) / 4 * sr ** 2))
        acc[c] = dict(a=bool(out[("dev", c)][0] >= 0.9 * out[("dev", "N1_alone")][0]), b=bool(out[("dev", c)][1] <= out[("dev", "N1_alone")][1]),
                      c=bool(out[("P1", c)][0] > 0 and out[("P2", c)][0] > 0), d=bool(p >= 0.95))
    okc = [c for c in acc if all(acc[c].values())]
    choice = max(okc, key=lambda c: out[("dev", c)][0]) if okc else None
    K = max(0.30, 1.25 * (out[("dev", choice)][1] if choice else out[("dev", "N1_alone")][1]))
    ok("V2", mx < 1e-9 and acc == cl["acceptance"] and choice == cl["choice"] and abs(K - cl["kill_K"]) < 1e-12,
       f"E-2 recomputed: max |Calmar diff| {mx:.1e}; acceptance {acc}; choice {choice}; K {K:.4f}")
    # V5
    reg = (O_ / "trial_registry_eco.csv").read_text().strip().splitlines()[1:]
    prev, chain = (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().strip().splitlines()[-1].split(",")[-1], True
    for l in reg:
        r = l.split(",")
        chain &= r[7] == prev and hashlib.sha256(",".join(r[:-1]).encode()).hexdigest() == r[8] \
            and hashlib.sha256(base64.b64decode(r[3][4:])).hexdigest() == r[4]
        prev = r[8]
    lock = (O_ / "ECO_PROTOCOL_SHA256.txt").read_text().split()[0]
    ok("V5", chain and cl["protocol_sha"] == lock == sha(O_ / "ECO_PROTOCOL_PREREGISTERED.md")
       and all(cl["files"][k] == sha(O_ / k) for k in cl["files"]) and all(cl["derived"][k] == sha(DER / k) for k in cl["derived"]),
       f"protocol lock {lock[:12]}, ECO registry chain ({len(reg)} lines), claims file and derived SHAs")


def v_replay(d1, d2):
    RP = DER / "replay"
    cfg = json.loads((R_ / "deploy" / "eco_config.json").read_text())
    L = [json.loads(l) for l in (Path(d1) / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    L2 = [json.loads(l) for l in (Path(d2) / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    filt = {}
    for s in json.loads((RP / "exchange_info.json").read_text(encoding="utf-8"))["symbols"]:
        if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT":
            f = {x["filterType"]: x for x in s["filters"]}
            filt[s["symbol"]] = (float(f["MARKET_LOT_SIZE"]["stepSize"]), float(f["MARKET_LOT_SIZE"]["minQty"]), float(f.get("MIN_NOTIONAL", {}).get("notional", 0)))
    n1L = [json.loads(l) for l in (RP / "n1" / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    f4o = json.loads((RP / "f4_orders.json").read_text(encoding="utf-8"))
    names = json.loads((RP / "manifest.json").read_text(encoding="utf-8"))["f4_names"]
    n1names = cfg["n1_perp_names"]

    def perp(coin):
        p = n1names.get(coin)
        if p in filt:
            return p, (1e3 if p.startswith("1000") and not coin.startswith("1000") else 1.0)
        v = names.get(coin)
        if v and v[0] in filt:
            return v[0], v[1]
        b = coin[:-4]
        for c, sc in ((coin, 1.0), (f"1000{b}USDT", 1e3), (f"1000000{b}USDT", 1e6)):
            if c in filt:
                return c, sc
        return None, None
    # ---- V3: targets of 200 random cycles
    rng = np.random.default_rng(2026)
    n1T = [pd.Timestamp(r["T"]) for r in n1L]
    bad, checked, capped = [], 0, 0
    for i in sorted(rng.choice(len(L), 200, replace=False)):
        r = L[i]
        if r.get("caps"):
            capped += 1
            continue
        now = pd.Timestamp(r["T"])
        tgt = {}
        j = max([q for q, T in enumerate(n1T) if T + pd.Timedelta(minutes=41) <= now], default=None)
        if j is not None and (now - n1T[j]) <= pd.Timedelta(hours=5):
            pos = {}
            for x in n1L[: j + 1]:
                for a in x["actions"]:
                    if a["a"] == "open":
                        pos[a["k"]] = (a["k"].split("|")[1], int(a["side"]), abs(a["notional"] / a["px"]))
                    else:
                        pos.pop(a["k"], None)
            eq = n1L[j]["equity"]
            for k, (coin, s, u) in pos.items():
                p, sc = perp(coin)
                if p is None or p not in r["price"] or "N1|" + k in r["suppressed"]:
                    continue
                tgt[p] = tgt.get(p, 0.0) + r["a"]["N1"] * r["E_m"] * r["k_m"] * s * u * r["price"][p] / sc / eq / r["price"][p]
        ds = [d for d in f4o if pd.Timestamp(d) + pd.Timedelta(days=1, hours=2, minutes=15) <= now]
        if ds:
            dec = f4o[max(ds)]
            eqf = sum(float(v["equity_close"]) for v in dec.values())
            for sl, v in dec.items():
                e = float(v["equity_close"])
                items = [(s, 1, u["units"] * 1.0, None) for s, u in v["longs"].items() if s not in v["sell"]] + \
                        [(s, 1, None, 0.5 * e / 5) for s in v["buy"]] + \
                        [(s, -1, u["units"] * 1.0, None) for s, u in v["shorts"].items() if s not in v["cover"]] + \
                        [(s, -1, None, 0.5 * e / 5) for s in v["short"]]
                for s, side, u, fs in items:
                    key = f"1D|{sl}|{'L' if side == 1 else 'S'}|{s}"
                    p, sc = perp(s)
                    if p is None or p not in r["price"] or key in r["suppressed"]:
                        continue
                    frac = side * (u * r["price"][p] / sc if u is not None else fs) / eqf
                    tgt[p] = tgt.get(p, 0.0) + r["a"]["1D"] * r["E_m"] * r["k_m"] * frac / r["price"][p]
        led = r["targets_net"]
        for p in set(tgt) | set(led):
            a_, b_ = tgt.get(p, 0.0), led.get(p, 0.0)
            if abs(a_ - b_) > 1e-9 * max(1.0, abs(a_)):
                bad.append((r["T"], p, a_, b_))
        # orders from the band rule
        band = cfg["band_frac"] * r["k_m"] * r["eco_equity_before"] if "eco_equity_before" in r else None
        checked += 1
    ok("V3", not bad and checked >= 150, f"targets of {checked} random cycles recomputed independently ({capped} capped cycles skipped): mismatches {len(bad)} {bad[:3]}")
    # ---- V4: R1 attribution identity, R3 caps, R5 minimums, R6 determinism
    r1 = max(abs(r["acct_pnl"] - r["sim_equity"]) for r in L)
    viol5 = []
    for r in L:
        for o in r["orders"]:
            st_, mq, mn = filt[o["perp"]]
            closes = abs(r["exch_before"].get(o["perp"], 0.0) + o["qty"]) < 1e-12
            if abs(o["qty"]) < mq - 1e-12 or (abs(o["qty"]) * r["price"][o["perp"]] < mn and not closes):
                viol5.append((r["T"], o))
    viol3 = []
    for r in L:
        E = r["eco_equity"]
        net = {p: q * r["price"].get(p, 0.0) / r["k_m"] for p, q in r["sim_pos"].items()}
        tol = cfg["band_frac"] * E
        for p, v in net.items():
            if abs(v) > cfg["coin_cap"] * E + tol + 0.02 * cfg["coin_cap"] * E:
                viol3.append((r["T"], p, round(v, 2)))
        if sum(abs(v) for v in net.values()) > cfg["gross_cap"] * E * 1.02 + tol:
            viol3.append((r["T"], "gross", round(sum(abs(v) for v in net.values()), 2)))
    same = [a["line_sha256"] for a in L] == [b["line_sha256"] for b in L2]
    ok("V4", r1 < 1e-6 and not viol5 and not viol3 and same,
       f"R1 max |attribution - simulated account| {r1:.2e} over {len(L)} cycles; R5 order-minimum violations {len(viol5)}; "
       f"R3 cap violations {len(viol3)} {viol3[:3]}; R6 two replays identical: {same}")
    # ---- R2 tracking against the paper combination, R4 stops
    eq_by_day = {pd.Timestamp(r["T"]).normalize(): r["eco_equity"] for r in L}
    n1d = {}
    for x in n1L:
        n1d[pd.Timestamp(x["T"]).normalize()] = x["equity"]
    days = sorted(d for d in eq_by_day)
    E, worst, prevN, prev1, a = E0, 0.0, n1d[pd.Timestamp("2026-08-31")], 30_000.0, L[-1]["a"]
    track = []
    for d in days:
        v1 = sum(float(v["equity_close"]) for v in f4o[str(d.date())].values()) if str(d.date()) in f4o else prev1
        r_n, r_1 = n1d[d] / prevN - 1, v1 / prev1 - 1
        E += E0 * (a["N1"] * r_n + a["1D"] * r_1)
        prevN, prev1 = n1d[d], v1
        track.append((str(d.date()), round(eq_by_day[d], 2), round(E, 2)))
        worst = max(worst, abs(eq_by_day[d] - E) / E0)
    stops = pd.read_csv(RP / "f4_stops.csv", parse_dates=["exit_time"])
    BL = {"D1": pd.Timedelta(days=1), "H4": pd.Timedelta(hours=4), "H1": pd.Timedelta(hours=1)}
    hit_at = {}
    for r in L:
        for k in r["stop_hits"]:
            hit_at.setdefault(k, []).append(pd.Timestamp(r["T"]))
    miss = []
    for s in stops.itertuples():
        key = f"1D|{s.sleeve}|S|{s.symbol}"
        hs = [t for t in hit_at.get(key, []) if t < s.exit_time + BL[s.sleeve] + pd.Timedelta(hours=1)]
        if not hs:
            miss.append((s.sleeve, s.symbol, str(s.exit_time)))
    ok("R2", worst <= 0.01, f"tracking: max |eco equity - paper combination| at day end = {100 * worst:.3f}% of E0 (gate 1.0%); last days {track[-3:]}")
    ok("R4", not miss, f"F4 stops in the window: {len(stops)}; executor component closed in or before the same F4 bar: {len(stops) - len(miss)}; missed {miss}")
    return track


def v_a1():
    """V6 ECO-T4 trades from raw 5m (own 1h / TF bars, own Wilder ATR); acceptance booleans. V7 outage-guard count."""
    cl = json.loads((O_ / "claims_eco_t4.json").read_text())
    T = pd.read_parquet(DER / "t4_trades_AC.parquet")
    rng = np.random.default_rng(4)
    pick = T.iloc[np.r_[rng.choice(np.flatnonzero(T.be_exit), 70, replace=False), rng.choice(np.flatnonzero(T.armed & ~T.be_exit), 70, replace=False),
                        rng.choice(np.flatnonzero(~T.armed), 60, replace=False)]].sort_values("coin")
    g0, H = pd.Timestamp("2020-02-01"), pd.Timedelta(hours=1)
    bad, cur = [], None
    for r in pick.itertuples():
        if r.coin != cur:
            x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{r.coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
            x["timestamp"] = pd.to_datetime(x.timestamp)
            g = x.groupby(x.timestamp.dt.floor("h"))
            h1 = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))
            tfb, cur = {}, r.coin
        if r.tf not in tfb:
            gg = h1.groupby(h1.index.floor("D") if r.tf == "1D" else h1.index.floor(r.tf))
            b = pd.DataFrame(dict(open=gg.open.first(), high=gg.high.max(), low=gg.low.min(), close=gg.close.last()))
            pc = b.close.shift(1).values
            tr = np.where(np.isnan(pc), b.high - b.low, np.maximum(b.high - b.low, np.maximum(abs(b.high - pc), abs(b.low - pc))))
            tfb[r.tf] = (b, pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values)
        b, atr = tfb[r.tf]
        en, A, s = float(b.open.iloc[r.e]), float(atr[r.e - 1]), int(r.side)
        hrs = h1.reindex(g0 + pd.to_timedelta(np.arange(r.a, r.E + 1), unit="h"))
        hi, lo, op = hrs.high.values, hrs.low.values, hrs.open.values
        span = r.E - r.a                                            # hours a .. E-1 are inside the trade
        exc = (hi[:span] >= en + 3 * A) if s == 1 else (lo[:span] <= en - 3 * A)
        arm = int(np.flatnonzero(exc)[0]) + r.a if exc.any() else -1
        ok_ = abs(en - r.entry) <= 1e-12 * en and (arm == r.h_arm) == True and bool(r.armed) == (arm >= 0)
        if arm >= 0:
            touch = (lo >= 0) & ((lo <= en) if s == 1 else (hi >= en))
            k0 = arm + 1 - r.a
            inside = touch[k0:span]
            if r.be_exit:
                fill = min(op[span], en) if s == 1 else max(op[span], en)
                ok_ &= (not inside.any()) and bool(touch[span]) and abs(fill - r.X) <= 1e-12 * en
            else:
                ok_ &= not inside.any()
        if not ok_:
            bad.append((r.coin, r.tf, str(r.entry_time), r.h_arm, arm))
    res4 = pd.read_csv(O_ / "T4_results.csv")
    c = {(x.window, x.config): x.calmar for x in res4.itertuples()}
    acc_a = all(c[(w, "T4")] > c[(w, "base")] for w in ("dev", "P1", "P2"))
    acc = dict(a=acc_a, b=bool(cl["dsr"]["p"] >= 0.95), c=bool(cl["combined_T4"]["dev"]["calmar"] >= cl["combined_ref_dev"]))
    ok("V6", not bad and acc == cl["acceptance"] and cl["verdict"].startswith("ECO-T4 FAIL") == (not all(acc.values())),
       f"200 T4 trades (70 break-even, 70 armed only, 60 never armed) recomputed from raw 5m: mismatches {len(bad)} {bad[:3]}; acceptance {acc} -> {cl['verdict']}")
    og = json.loads((O_ / "A1_outage_guard.json").read_text())
    tot, n5 = 0, 0
    for f in sorted((R_ / "data" / "futures_um").glob("*_perp_1h.csv.gz")):
        d = pd.read_csv(f, usecols=["timestamp", "high", "low", "close"]).sort_values("timestamp")
        p = d.close.shift(1)
        m = p.notna() & (p > 0)
        tot += int(m.sum()); n5 += int((m & ((d.high >= 1.5 * p) | (d.low <= 0.5 * p))).sum())
    ok("V7", tot == og["coin_hours"] and n5 == og["count"]["0.5"] and og["chosen_D"] == (0.5 if n5 / tot <= 1e-4 else 0.6),
       f"outage guard count recomputed: {n5} of {tot} coin-hours ({n5 / tot:.2e}) -> D {og['chosen_D']}")


if __name__ == "__main__":
    a = sys.argv[1:] or ["e2"]
    if "a1" in a:
        v_a1()
    if "e2" in a:
        v_e2()
    if "replay" in a:
        i = a.index("replay")
        v_replay(a[i + 1], a[i + 2])
    print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
    sys.exit(1 if False in res else 0)
