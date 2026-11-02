"""
N3 EVT tail-risk monitor (protocol: logs/monitor_n3_evt/N3_PROTOCOL_PREREGISTERED.md). Information only, no orders.
Each day: fit a POT / GPD tail on the backtest + forward daily losses of each line, write tomorrow's 1-day VaR / ES
(99 %, 99.9 %), and record whether yesterday's forward loss exceeded the estimate written for it.
Usage: pythonw n3_evt_monitor.py
"""
import sys
import json
import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR,):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import LOGS_DIR

LOG = LOGS_DIR / "monitor_n3_evt"
PROTO = LOG / "N3_PROTOCOL_PREREGISTERED.md"
LEDGER = LOG / "ledger.csv"
F7 = LOGS_DIR / "strategy_f7_risk"
F4 = LOGS_DIR / "forward_ls_f4"
PS = (0.99, 0.999)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def pot(losses, q=0.90):
    """POT / GPD tail: returns dict(u, xi, beta, n, n_u, VaR99, ES99, VaR999, ES999)."""
    L = np.asarray(losses, float)
    L = L[np.isfinite(L)]
    n = len(L)
    u = float(np.quantile(L, q))
    y = L[L > u] - u
    xi, _, beta = stats.genpareto.fit(y, floc=0)
    out = dict(u=u, xi=float(xi), beta=float(beta), n=n, n_u=int(len(y)))
    for p in PS:
        tail = (n / len(y)) * (1 - p)
        var = u + (beta / xi) * (tail ** (-xi) - 1) if abs(xi) > 1e-9 else u - beta * np.log(tail)
        es = var / (1 - xi) + (beta - xi * u) / (1 - xi) if xi < 1 else np.inf
        tag = "99" if p == 0.99 else "999"
        out[f"VaR{tag}"], out[f"ES{tag}"] = float(var), float(es)
    return out


def backtest_returns(name):
    e = pd.read_csv(F7 / f"equity_MAIN_AI_{name}.csv", parse_dates=["date"]).set_index("date").M_AI3
    return e.pct_change().dropna()


def forward_returns(line):
    """daily returns of a forward line from the F4 ledger lines (LS_RS / LO), in as-of order."""
    if not (F4 / "ledger.csv").exists():
        return pd.Series(dtype=float)
    L = pd.read_csv(F4 / "ledger.csv")
    s = pd.Series(L[line].values, index=pd.to_datetime(L["asof"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.pct_change().dropna()


def main():
    assert sha_bytes(PROTO.read_bytes()) == (LOG / "N3_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"
    now = pd.Timestamp.now("UTC").tz_localize(None)
    rows = []
    for line, bt in (("LS_RS", "RS"), ("LO", "OFF_LO")):
        r_bt, r_fw = backtest_returns(bt), forward_returns(line)
        last_fw = r_fw.index.max() if len(r_fw) else None
        est = pot(-np.r_[r_bt.values, r_fw.values])
        # exceedance of the estimate written for the latest forward day (the previous ledger line of this line)
        exc99 = exc999 = None
        if LEDGER.exists() and last_fw is not None:
            P = pd.read_csv(LEDGER)
            P = P[(P.line == line) & (P.target_day == str(last_fw.date()))]
            if len(P):
                loss = -float(r_fw.loc[last_fw])
                exc99, exc999 = bool(loss > P.VaR99.iloc[-1]), bool(loss > P.VaR999.iloc[-1])
        led_last = pd.to_datetime(pd.read_csv(F4 / "ledger.csv")["asof"]).max() if (F4 / "ledger.csv").exists() else None
        assert led_last is not None, "F4 ledger missing: nothing to monitor yet"
        target = led_last + pd.Timedelta(days=1)                 # the next forward as-of day
        rows.append(dict(run_utc=str(now), line=line, n_backtest=len(r_bt), n_forward=len(r_fw), target_day=str(target.date()),
                         last_forward_day=str(last_fw.date()) if last_fw is not None else None,
                         last_forward_exceeded_VaR99=exc99, last_forward_exceeded_VaR999=exc999, **{k: (round(v, 8) if isinstance(v, float) else v) for k, v in est.items()}))
    LOG.mkdir(parents=True, exist_ok=True)
    prev = pd.read_csv(LEDGER).line_sha256.iloc[-1] if LEDGER.exists() else "GENESIS"
    for r in rows:
        if LEDGER.exists():
            P = pd.read_csv(LEDGER)
            if ((P.line == r["line"]) & (P.target_day == r["target_day"])).any():
                print(f"{r['line']} {r['target_day']} already estimated -> skip")
                continue
        r["code_sha256"] = sha_bytes(Path(__file__).read_bytes())
        r["prev_sha256"] = prev
        r["line_sha256"] = sha_bytes(json.dumps(r, sort_keys=True, default=str).encode())
        prev = r["line_sha256"]
        pd.DataFrame([r]).to_csv(LEDGER, mode="a", index=False, header=not LEDGER.exists())
        print(f"{r['line']}: target {r['target_day']} VaR99 {r['VaR99']:.4f} ES99 {r['ES99']:.4f} VaR99.9 {r['VaR999']:.4f} "
              f"(xi {r['xi']:.3f}, n {r['n']}, forward {r['n_forward']}); last forward exceeded VaR99: {r['last_forward_exceeded_VaR99']}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.mkdir(parents=True, exist_ok=True)
        with open(LOG / "run_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{pd.Timestamp.now('UTC')}] RUN FAILED\n{traceback.format_exc()}\n")
        sys.exit(1)
