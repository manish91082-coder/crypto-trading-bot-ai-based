"""Independent verifier for DDX (protocol logs/drawdown_ddx/DDX_PROTOCOL_PREREGISTERED.md).
Own code: csv / json / pyarrow reading, plain loops for drawdowns and percentiles, its own stationary bootstrap
(random.Random(777)). Checks X1-X8.  Run: python src/audits/verify_drawdown_ddx.py"""
import csv, hashlib, json, math, random
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "drawdown_ddx"
res = []


def check(n, ok, d=""):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                return h.hexdigest()
            h.update(b)


def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def maxdd(vals):
    peak, worst = vals[0], 0.0
    for v in vals:
        if v > peak:
            peak = v
        d = 1 - v / peak
        if d > worst:
            worst = d
    return worst


def pct(xs, q):                       # numpy 'linear' definition
    s = sorted(xs)
    pos = (len(s) - 1) * q / 100
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def close(a, b, t=1e-9):
    return abs(a - b) <= t * max(1.0, abs(a), abs(b))


def J(folder, f):
    return json.loads((ROOT / folder / f).read_text())


# (id, item, claimed dd pct, claimed final, equity file, column, prepend E0, unrounded)
def claim_specs():
    s = []
    c = J("logs/strategy_1d_step19_largecap", "claims.json")["portfolio"]
    s += [("A01", "AI", c["AI"]["max_dd_pct"], c["AI"]["final"], "logs/strategy_1d_step19_largecap/AI_equity.csv", "equity"),
          ("A01", "BTC_HOLD", c["BTC_HOLD"]["max_dd_pct"], c["BTC_HOLD"]["final"], "logs/strategy_1d_step19_largecap/BTC_HOLD_equity.csv", "equity")]
    c = J("logs/strategy_1d_step17_18", "claims.json")["portfolio"]
    s += [("A02", n, c[n]["max_dd_pct"], c[n]["final"], f"logs/strategy_1d_step17_18/{n}_equity.csv", "equity") for n in ("FULL", "R5_ONLY")]
    c = J("logs/strategy_1d_step20_largecap_gate", "claims.json")["portfolio"]
    s += [("A03", n, c[n]["max_dd_pct"], c[n]["final"], f"logs/strategy_1d_step20_largecap_gate/{n}_equity.csv", "equity") for n in ("GATED", "UNGATED")]
    c = J("logs/strategy_1d_step21_crash", "claims.json")["portfolio"]
    s += [("A04", n, c[n]["max_dd_pct"], c[n]["final"], f"logs/strategy_1d_step21_crash/{n}_equity.csv", "equity") for n in ("ALARM", "ALARM_CONTROL", "UNGATED")]
    c = J("logs/strategy_1d_step26_exit", "claims.json")["main"]
    s += [("A05", "AI_VETO", c["AI_VETO"]["max_dd_pct"], c["AI_VETO"]["final"], "logs/strategy_1d_step26_exit/MAIN_2021_26_AI_VETO_daily_equity.csv", "equity")]
    dt = rows(ROOT / "logs/strategy_1d_step27_combine/decision_table.csv")
    for f, tag in (("1.0", "100"), ("0.75", "75"), ("0.5", "50"), ("0.3", "30")):
        r = [x for x in dt if x["mix"] == "D1" and abs(float(x["f"]) - float(f)) < 1e-12][0]
        s.append(("A06", f"D1 f={f}", float(r["MAIN_max_dd_pct"]), float(r["MAIN_final"]), f"logs/strategy_1d_step27_combine/sleeves_MAIN_f{tag}.csv", "D1"))
    c = J("logs/strategy_1d_step28_volsize", "claims.json")["MAIN"]["VOL"]
    s.append(("A07", "MAIN.VOL", c["max_dd_pct"], c["final"], "logs/strategy_1d_step28_volsize/vol_path_MAIN.csv", "equity"))
    c = J("logs/strategy_f2_longshort", "claims.json")["MAIN"]
    s += [("A08", f"MAIN.{n}", c[n]["mix"]["max_dd_pct"], c[n]["mix"]["final"], f"logs/strategy_f2_longshort/equity_MAIN_{f}.csv", "M_AI3")
          for n, f in (("AI_LS", "AI_LS"), ("AI_LO", "AI_LO"))]
    c = J("logs/strategy_f7_risk", "claims.json")["MAIN"]
    s += [("A09", f"MAIN.{n}", c[n]["mix"]["max_dd_pct"], c[n]["mix"]["final"], f"logs/strategy_f7_risk/equity_MAIN_AI_{n}.csv", "M_AI3")
          for n in ("RS", "OFF_LS")]
    for rid, cf, names in (("A10", "claims_E1.json", ("E1a", "E1b")), ("A11", "claims_E4.json", ("E4",))):
        c = J("logs/research_r1", cf)
        s += [(rid, n, c["results"][n]["result"]["mix"]["max_dd_pct"], c["results"][n]["result"]["mix"]["final"],
               f"logs/research_r1/equity_{n}.csv", "M_AI3") for n in names]
        s.append((rid, "baseline F7 RS", c["baseline"]["max_dd_pct"], c["baseline"]["final"], "logs/research_r1/equity_BASE_F7_RS.csv", "M_AI3"))
    return [x + (False,) for x in s]


def main():
    # X1 protocol + output SHAs
    check("X1 protocol SHA", sha(OUT / "DDX_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0])
    good = all(sha(OUT / l.split()[1]) == l.split()[0] for l in (OUT / "OUTPUT_SHA256.txt").read_text().splitlines())
    check("X1 output SHAs", good)
    check("X1 input SHAs", all(sha(ROOT / r["file"]) == r["sha256"] for r in rows(OUT / "input_manifest.csv")))
    # X2 protocol SHA checks of the 16 past studies, own parsing
    S = rows(OUT / "sha_checks.csv")
    prot = [r for r in S if r["kind"] == "protocol"]
    mine_ok = []
    for r in prot:
        d = ROOT / r["sha_file"].rsplit("/", 1)[0]
        p = d / r["file"] if (d / r["file"]).exists() else ROOT / r["file"]
        mine_ok.append(sha(p) == r["stored"] and r["ok"] == "True" and r["claims_match"] == "True")
    check("X2 past protocol SHAs (16 studies)", all(mine_ok) and len({r["id"] for r in prot}) == 16, f"{sum(mine_ok)}/{len(prot)} files")
    # X3 drawdown + final recomputation per ledger row
    L = {(r["id"], r["item"]): r for r in rows(OUT / "ledger.csv")}
    n_dd = n_fin = 0
    allok = True
    for rid, item, cdd, cfin, path, col, _ in claim_specs():
        v = [float(r[col]) for r in rows(ROOT / path)]
        dd, fin = maxdd(v) * 100, v[-1]
        lr = L[(rid, item)]
        ok = close(dd, float(lr["recomputed_dd_pct"])) and close(fin, float(lr["recomputed_final"])) and abs(dd - cdd) <= 0.01 + 1e-12
        n_dd += abs(dd - cdd) <= 0.01 + 1e-12
        n_fin += abs(fin - cfin) <= 0.01 + 1e-9
        ok &= (lr["final_ok"] == "True") == (abs(fin - cfin) <= 0.01 + 1e-9)
        allok &= ok
        if not ok:
            print("   mismatch", rid, item, dd, cdd, fin, cfin)
    check("X3 ledger drawdowns (rounded claims)", allok, f"DD match {n_dd}, final match {n_fin} (others = close-out gap, X4)")
    # ECO rows: pyarrow, E0 prepended, unrounded
    t = pq.read_table(ROOT / "data/derived/eco/e2_daily_series.parquet").to_pydict()
    c = J("logs/eco", "claims_eco_e2.json")["results"]
    e2 = {(r["window"], r["config"]): float(r["final"]) for r in rows(ROOT / "logs/eco/E2_results.csv")}
    ok = True
    for key in ("dev|ECO-W2", "dev|1D_alone_combo", "dev|N1_alone", "P3|ECO-W2", "P3|1D_alone_combo", "P3|N1_alone"):
        v = [10_000.0] + [x for x in t[key] if x is not None and x == x]
        dd = maxdd(v)
        lr = L[("A12", key)]
        ok &= close(dd, c[key]["mtm_dd"]) and close(dd * 100, float(lr["recomputed_dd_pct"])) and close(v[-1], e2[tuple(key.split("|"))])
    check("X3 ECO rows (unrounded, 1e-9)", ok)
    # X4 close-out explanation, own arithmetic on two rows
    tr = rows(ROOT / "logs/strategy_1d_step19_largecap/AI_trades.csv")
    eq = rows(ROOT / "logs/strategy_1d_step19_largecap/AI_equity.csv")
    fee = sum(float(r["cost"]) / 1.0025 / float(r["entry"]) * float(r["exit"]) for r in tr if r["reason"] == "end_of_test") * 0.0025
    a01 = abs(float(eq[-1]["equity"]) - fee - 65274.51) <= 0.01
    rs = sum(10_000 + sum(float(r["pnl"]) for r in rows(ROOT / f"logs/strategy_f7_risk/trades_MAIN_{s}_AI_RS.csv")) for s in ("D1", "H4", "H1")) / 3
    a09 = abs(rs - 88400.87) <= 0.01
    G = rows(OUT / "final_gap_investigation.csv")
    n_exact = sum(r["explained"] == "True" for r in G)
    check("X4 final gap = end close-out fee", a01 and a09 and n_exact == 14 and len(G) == 19,
          f"A01 {a01}, A09 {a09}; investigation exact {n_exact}/19, bound-only 4, no trades file 1")
    # returns for Part B
    rets = {}
    for w in ("dev", "P3"):
        v = [x for x in t[f"{w}|ECO-W2"] if x is not None and x == x]
        prev = [10_000.0] + v[:-1]
        rets[w] = [a / b - 1 for a, b in zip(v, prev)]
    rets["ALL"] = rets["dev"] + rets["P3"]
    rets["DEV"] = rets["dev"]
    # X5 rolling windows exact
    R = rows(OUT / "rolling_windows.csv")
    ok = True
    for r in R:
        x = rets[r["base"]]
        H = int(r["H"])
        dds, rts = [], []
        for i in range(len(x) - H + 1):
            e, peak, w = 1.0, 1.0, 0.0
            for j in range(i, i + H):
                e *= 1 + x[j]
                if e > peak:
                    peak = e
                if 1 - e / peak > w:
                    w = 1 - e / peak
            dds.append(w)
            rts.append(e - 1)
        ok &= len(dds) == int(r["n_windows"]) and close(max(dds), float(r["dd_max"])) and close(pct(dds, 95), float(r["dd_p95"])) \
            and close(pct(dds, 50), float(r["dd_p50"])) and close(pct(rts, 50), float(r["ret_p50"])) and close(min(rts), float(r["ret_min"])) \
            and close(sum(q < 0 for q in rts) / len(rts), float(r["share_ret_lt_0"]))
    check("X5 rolling windows (exact)", ok, f"{len(R)} rows")
    # X6 own stationary bootstrap, seed 777, ALL and P3
    B = {(r["base"], int(r["H"])): r for r in rows(OUT / "band_bootstrap.csv")}
    kill = json.loads((ROOT / "deploy/eco_config.json").read_text())["kill_K"]
    rnd = random.Random(777)
    worst = 0.0
    ok = True
    mine = {}
    for b in ("ALL", "P3"):
        x = rets[b]
        n = len(x)
        for H in (30, 90, 180, 365):
            dds, kills = [], 0
            for _ in range(10_000):
                k = rnd.randrange(n)
                e, peak, w = 1.0, 1.0, 0.0
                for step in range(H):
                    if step and rnd.random() < 1 / 20:
                        k = rnd.randrange(n)
                    elif step:
                        k = (k + 1) % n
                    e *= 1 + x[k]
                    if e > peak:
                        peak = e
                    if 1 - e / peak > w:
                        w = 1 - e / peak
                dds.append(w)
                kills += w >= kill
            p95, p99 = pct(dds, 95), pct(dds, 99)
            r = B[(b, H)]
            d = max(abs(p95 - float(r["dd_p95"])), abs(p99 - float(r["dd_p99"])), abs(kills / 1e4 - float(r["P_dd_ge_kill"])))
            worst = max(worst, d)
            ok &= d <= 0.01
            mine[(b, H)] = (p95, p99, kills / 1e4)
            print(f"   own boot {b} H{H}: p95 {p95:.4f} (main {float(r['dd_p95']):.4f}) p99 {p99:.4f} (main {float(r['dd_p99']):.4f}) P(kill) {kills/1e4:.4f}")
    check("X6 own bootstrap within 1.0 pp", ok, f"worst diff {worst * 100:.2f} pp")
    # X7 alarm thresholds = ALL band p95 / p99
    A = rows(OUT / "alarm_thresholds.csv")
    check("X7 alarm thresholds", len(A) == 4 and all(close(float(a["yellow_dd"]), float(B[("ALL", int(a["H"]))]["dd_p95"]))
                                                   and close(float(a["red_dd"]), float(B[("ALL", int(a["H"]))]["dd_p99"])) for a in A))
    # X8 statements
    Rj = json.loads((OUT / "RESULTS.json").read_text())
    pk = float(B[("ALL", 365)]["P_dd_ge_kill"])
    p3 = float(B[("P3", 365)]["ret_p50"])
    check("X8 statements §3", Rj["statement2"] == ("realistic within a year" if pk > 0.10 else "tail event (<=10%)")
          and Rj["statement3"] == (p3 <= 0) and Rj["partA_verified"] is False and len(Rj["sha_failures"]) == 3
          and all(f["kind"] == "other" for f in Rj["sha_failures"]),
          f"P(kill 365|ALL) {pk}, P3 median 365 {p3:.4f}; partA_verified False due to close-out gaps only")
    print(f"\nTOTAL {len(res)} checks, {sum(res)} PASS, {len(res) - sum(res)} FAIL -> {'ALL PASS' if all(res) else 'FAILURES'}")


if __name__ == "__main__":
    main()
