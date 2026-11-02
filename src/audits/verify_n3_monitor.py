"""
Independent verifier for the N3 monitor ledger (logs/monitor_n3_evt/ledger.csv).
V1 protocol hash; hash chain (every line_sha256 re-computed, prev links).
V2 for every ledger line: rebuild the loss sample (F7 backtest equity + F4 forward ledger up to the line's last forward
   day), recompute u (plain sorted-array quantile), refit the GPD by maximising the log-likelihood with scipy.optimize
   (independent of scipy.stats.genpareto.fit), and recompute VaR / ES with the formulas written out here. Tolerance:
   u exact; VaR / ES within 1 % (two different optimisers).
V3 exceedance flags re-derived from the forward loss and the estimate written for that day.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "execution"))
import n3_evt_monitor as M


def sha(b):
    return hashlib.sha256(b).hexdigest()


def gpd_mle(y):
    def nll(par):
        xi, lb = par
        b = np.exp(lb)
        z = 1 + xi * y / b
        if np.any(z <= 0):
            return 1e18
        return len(y) * lb + (1 + 1 / xi) * np.log(z).sum() if abs(xi) > 1e-8 else len(y) * lb + y.sum() / b
    r = optimize.minimize(nll, x0=[0.1, np.log(y.mean())], method="Nelder-Mead", options=dict(xatol=1e-10, fatol=1e-12, maxiter=20000))
    return r.x[0], float(np.exp(r.x[1]))


def main():
    assert sha(M.PROTO.read_bytes()) == (M.LOG / "N3_PROTOCOL_SHA256.txt").read_text().split()[0]
    L = pd.read_csv(M.LEDGER)
    prev = "GENESIS"
    for r in L.to_dict("records"):
        line = {k: v for k, v in r.items() if k != "line_sha256"}
        for k, v in line.items():
            if isinstance(v, float) and np.isnan(v):
                line[k] = None
            elif isinstance(v, (np.bool_,)):
                line[k] = bool(v)
            elif isinstance(v, np.integer):
                line[k] = int(v)
            elif isinstance(v, np.floating):
                line[k] = float(v)
        assert r["prev_sha256"] == prev, "chain"
        assert sha(json.dumps(line, sort_keys=True, default=str).encode()) == r["line_sha256"], ("line hash", r["line"], r["target_day"])
        prev = r["line_sha256"]
    print(f"[V1 PASS] protocol; {len(L)} ledger lines, hash chain intact")
    for r in L.itertuples():
        bt = M.backtest_returns("RS" if r.line == "LS_RS" else "OFF_LO")
        fw = M.forward_returns(r.line)
        if isinstance(r.last_forward_day, str):
            fw = fw[fw.index <= pd.Timestamp(r.last_forward_day)]
        else:
            fw = fw.iloc[:0]
        loss = np.sort(-np.r_[bt.values, fw.values])
        n = len(loss)
        assert n == r.n, (n, r.n)
        u = float(np.quantile(loss, 0.90))
        assert abs(u - r.u) < 1e-8, (u, r.u)
        y = loss[loss > u] - u
        xi, beta = gpd_mle(y)
        for p, tag in ((0.99, "99"), (0.999, "999")):
            tail = (n / len(y)) * (1 - p)
            var = u + beta / xi * (tail ** (-xi) - 1)
            es = var / (1 - xi) + (beta - xi * u) / (1 - xi)
            assert abs(var / getattr(r, f"VaR{tag}") - 1) < 0.01 and abs(es / getattr(r, f"ES{tag}") - 1) < 0.01, (r.line, tag, var, es)
    print(f"[V2 PASS] every line: sample size, threshold exact; GPD re-fitted with an independent optimiser; VaR / ES within 1 %")
    for r in L.itertuples():
        if isinstance(r.last_forward_day, str) and str(r.last_forward_exceeded_VaR99) in ("True", "False"):
            P = L[(L.line == r.line) & (L.target_day == r.last_forward_day)]
            loss = -float(M.forward_returns(r.line).loc[pd.Timestamp(r.last_forward_day)])
            assert (loss > P.VaR99.iloc[-1]) == (str(r.last_forward_exceeded_VaR99) == "True")
    print("[V3 PASS] exceedance flags re-derived")


if __name__ == "__main__":
    main()
