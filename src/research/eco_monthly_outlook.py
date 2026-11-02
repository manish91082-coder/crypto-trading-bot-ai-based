"""ECO 10,000 USDT monthly outlook, descriptive (logs/eco/monthly_outlook/MONTHLY_OUTLOOK_PROTOCOL_PREREGISTERED.md).
Run: python src/research/eco_monthly_outlook.py"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
OUT = PROJ / "logs" / "eco" / "monthly_outlook"
PAR = PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet"
LIVE = OUT / "live" / "eco_plan_ledger_snapshot.jsonl"
Q = [10, 25, 50, 75, 90]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


assert sha(OUT / "MONTHLY_OUTLOOK_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


def dist(r):
    r = np.asarray(r, float)
    d = dict(n=int(len(r)), worst=float(r.min()), mean=float(r.mean()), best=float(r.max()), share_pos=float((r > 0).mean()))
    d.update({f"p{q}": float(np.percentile(r, q)) for q in Q})
    d["usdt"] = {k: round(10_000 * (1 + v), 2) for k, v in d.items() if k in ("worst", "p10", "p25", "p50", "mean", "p75", "p90", "best")}
    return d


def window(s):
    s = s.dropna()
    me = s.groupby(s.index.to_period("M")).last()
    base = pd.concat([pd.Series([s.iloc[0]], index=[me.index[0] - 1]), me])
    mr = (base / base.shift(1) - 1).dropna()
    r30 = (s.shift(-30) / s.shift(1) - 1).dropna()                        # equity at d+30 / equity at d-1
    dd30 = []
    v = s.values
    for i in range(len(v) - 30):
        w = v[i:i + 31]
        dd30.append(float((w / np.maximum.accumulate(w) - 1).min()))
    m3 = (base / base.shift(3) - 1).dropna()
    return dict(start=str(s.index[0].date()), end=str(s.index[-1].date()), first=float(s.iloc[0]), last=float(s.iloc[-1]),
                total_return=float(s.iloc[-1] / s.iloc[0] - 1), max_dd=float((s / s.cummax() - 1).min()),
                months=dist(mr.values), month_list={str(k): float(x) for k, x in mr.items()},
                rolling30=dist(r30.values), worst_dd_within_30d=float(min(dd30)), worst_3_months=float(m3.min()),
                worst_3_months_end=str(m3.idxmin()))


def main():
    E = pd.read_parquet(PAR)
    res = dict(protocol_sha256=sha(OUT / "MONTHLY_OUTLOOK_PROTOCOL_PREREGISTERED.md"), code_sha256=sha(__file__), parquet_sha256=sha(PAR),
               live_snapshot_sha256=sha(LIVE))
    for w in ("P3", "dev"):
        res[w] = window(E[f"{w}|ECO-W2"])
    L = [json.loads(l) for l in LIVE.read_text().splitlines() if l.strip()]
    ok = [r for r in L if r.get("ok") and r.get("eco_equity") is not None and r.get("mode") != "reset"]
    eq = [r["eco_equity"] for r in ok]
    res["live_plan"] = dict(n_records=len(L), n_ok=len(ok), first_T=ok[0]["T"], last_T=ok[-1]["T"], first=eq[0], last=eq[-1], min=min(eq), max=max(eq),
                            days=(pd.Timestamp(ok[-1]["T"]) - pd.Timestamp(ok[0]["T"])) / pd.Timedelta(days=1), ret=eq[-1] / 10_000 - 1)
    cfg = json.loads((PROJ / "deploy" / "eco_config.json").read_text())
    res["limits"] = dict(kill_K=cfg["kill_K"], guard_D=cfg["guard_D"], coin_cap=cfg["coin_cap"], gross_cap=cfg["gross_cap"], config_sha256=sha(PROJ / "deploy" / "eco_config.json"))
    res["execution_gap_E3"] = dict(window="2026-09", executor=9817.25, paper=9697.27, source="logs/eco/E3_E4_RESULTS.md",
                                   note="recorded; R2 tracking gate FAILED (1.20% > 1.0%); not blended")
    f = OUT / "MONTHLY_OUTLOOK_RESULTS.json"
    f.write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "RESULTS_SHA256.txt").write_text(sha(f) + "  MONTHLY_OUTLOOK_RESULTS.json\n")
    for w in ("P3", "dev"):
        m = res[w]["months"]
        print(w, res[w]["start"], res[w]["end"], "total", round(res[w]["total_return"], 4), "maxdd", round(res[w]["max_dd"], 4),
              "| months n", m["n"], "usdt", m["usdt"], "share+", round(m["share_pos"], 3),
              "| roll30 usdt", res[w]["rolling30"]["usdt"], "| worst dd in 30d", round(res[w]["worst_dd_within_30d"], 4),
              "| worst 3m", round(res[w]["worst_3_months"], 4), res[w]["worst_3_months_end"])
        print("  months:", {k: round(v * 100, 2) for k, v in res[w]["month_list"].items()})
    print("live", res["live_plan"])


if __name__ == "__main__":
    main()
