"""Independent verifier for N2 (logs/research_n2_regime/N2_PROTOCOL_PREREGISTERED.md section 5). Own code; does not import n2_regime /
n1_portfolio. W1 R1 states + m_vol from raw BTC data   W2 R2: stored objectives re-derived from stored centroids (own DP) for 5 months,
online states for 100 random days   W3 regime weights = N1 FINAL weight x g for every matched entry   W4 gates from the result files
W5 SHAs + registry T16"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_n2_regime"
O1 = R_ / "logs" / "research_n1_portfolio"
DR = R_ / "data" / "derived" / "n1"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cl = json.loads((O_ / "claims_n2.json").read_text())
c1 = json.loads((O1 / "claims_n1.json").read_text())
# ---- own BTC daily closes ----
a = pd.read_csv(R_ / "data" / "universe_pre2020" / "1h" / "BTCUSDT_1h_full.csv.gz", usecols=["timestamp", "close"])
a["d"] = pd.to_datetime(a.timestamp).dt.floor("D")
a = a[a.d < "2020-01-01"]
b = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / "BTCUSDT_5m_full.csv.gz", usecols=["timestamp", "close"])
b["d"] = pd.to_datetime(b.timestamp).dt.floor("D")
c = pd.concat([a.groupby("d").close.last(), b.groupby("d").close.last()]).sort_index()
r = c.pct_change()
sd20 = r.rolling(20).std()
mv = np.minimum(1.0, sd20.expanding(min_periods=365).median() / sd20).fillna(1.0)
e20 = c.ewm(span=20, adjust=False).mean(); e50 = c.ewm(span=50, adjust=False).mean()
s1 = (e20 - e50 > 0).astype(int)
S = pd.read_csv(O_ / "N2_states.csv", header=[0, 1], index_col=0, parse_dates=True)
R1 = S["R1"].dropna()
gl = np.where(s1 == 1, 1.0, 0.25) * mv; gs = np.where(s1 == 1, 0.25, 1.0) * mv
own = pd.DataFrame(dict(gL=gl, gS=gs, state=s1, mvol=mv), index=c.index).reindex(R1.index)
d1 = float(np.nanmax(np.abs(own.values - R1[["gL", "gS", "state", "mvol"]].values)))
ok("W1", d1 < 1e-12 and len(R1) == len(c), f"R1 state / m_vol / g from own BTC daily closes ({len(c)} days): max diff {d1:.1e}")

# ---- W2 ----
F = pd.read_csv(O_ / "N2_fits.csv")
lr = np.log(c).diff()
feat = {}
for hl in (10, 21):
    dd = np.sqrt((np.minimum(lr, 0) ** 2).ewm(halflife=hl).mean())
    feat[f"dd{hl}"] = dd; feat[f"so{hl}"] = lr.ewm(halflife=hl).mean() / dd
X = pd.DataFrame(feat)
LAM = 50.0


def own_dp(Z, mu):
    cost = np.array([[((z - m) ** 2).sum() for m in mu] for z in Z])
    V = cost[0].copy(); back = []
    for t in range(1, len(Z)):
        nv = np.empty(2); bk = np.empty(2, int)
        for k in (0, 1):
            cand = [V[j] + (0 if j == k else LAM) for j in (0, 1)]
            bk[k] = int(np.argmin(cand)) if cand[0] != cand[1] else k
            nv[k] = cost[t, k] + min(cand)
        back.append(bk); V = nv
    s = [int(np.argmin(V))]
    for bk in reversed(back):
        s.append(int(bk[s[-1]]))
    s = np.array(s[::-1])
    return float(cost[np.arange(len(Z)), s].sum() + LAM * (np.diff(s) != 0).sum())


rng = np.random.default_rng(11)
bad = []
for i in rng.choice(len(F), 5, replace=False):
    f = F.iloc[i]
    ms = pd.Timestamp(f.month)
    tr = (X.index >= "2017-09-15") & (X.index < ms)
    mean, sdv = np.array(json.loads(f["mean"])), np.array(json.loads(f["sd"]))
    Z = ((X[tr].values - mean) / sdv)
    o = own_dp(Z, np.array(json.loads(f.mu)))
    if abs(o - f.obj) > 1e-6 * max(1, abs(f.obj)):
        bad.append(f"{f.month}: obj {o:.4f} vs {f.obj:.4f}")
R2 = S["R2"].dropna()
days = R2.index[rng.choice(len(R2), 100, replace=False)]
bad2 = 0
for d in days:
    ms = (d + pd.Timedelta(days=1)).to_period("M").to_timestamp()
    f = F[F.month == str(ms.date())].iloc[0]
    mu = np.array(json.loads(f.mu)); mean, sdv = np.array(json.loads(f["mean"])), np.array(json.loads(f["sd"]))
    up = (X.index >= "2017-09-15") & (X.index <= d)
    Z = (X[up].values - mean) / sdv
    V = ((Z[0] - mu) ** 2).sum(1)
    for z in Z[1:]:
        cst = ((z - mu) ** 2).sum(1)
        V = np.array([cst[0] + min(V[0], V[1] + LAM), cst[1] + min(V[1], V[0] + LAM)])
    st = 1 if int(np.argmin(V)) == int(f.bull) else 0
    bad2 += int(st != int(R2.state.loc[d]))
ok("W2", not bad and bad2 == 0, f"R2: 5 fit objectives re-derived from stored centroids (mismatch {bad}); 100 online states (mismatch {bad2})")

# ---- W3 ----
chosen = cl["chosen"] or "R1"
L2 = pd.read_parquet(DR / f"n2_trades_{chosen}.parquet")
L1 = pd.read_parquet(DR / f"trades_{c1['final_name']}.parquet")
key = ["sleeve", "coin", "tf", "fam", "side", "entry_time"]
m = L2.merge(L1[key + ["w"]], on=key, suffixes=("", "_n1"))
g = S[chosen].copy()
day = pd.DatetimeIndex(m.entry_time).floor("D") - pd.Timedelta(days=1)
gg = g.reindex(day)
fac = np.where(m.sleeve.isin(["A", "B"]), gg.gL.fillna(1.0).values, np.where(m.sleeve == "C", gg.gS.fillna(1.0).values, 1.0))
heat = c1["final_cfg"].get("heat", False)
d3 = float(np.max(np.abs(m.w - m.w_n1 * fac))) if not heat else float("nan")
ok("W3", len(m) == len(L2) == len(L1) and (heat or d3 < 1e-15), f"{chosen}: {len(m)} entries matched to N1 FINAL; max |w - w_N1 x g| {d3:.1e}"
   + (" (heat cap in base: ratio check not applicable)" if heat else ""))

# ---- W4 ----
Rr = pd.read_csv(O_ / "N2_results.csv")
cal = {(x.variant, x.window): x.calmar for x in Rr.itertuples()}
ddm = {(x.variant, x.window): x.mtm_dd for x in Rr.itertuples()}
RN = pd.read_csv(O_ / "N2_random.csv")
okg = True
for v in ("R1", "R2"):
    q = cl["results"][v]["gates"]
    okg &= q["Q1_dev_calmar_up_dd_down"] == bool(cal[(v, "dev")] > cal[("base", "dev")] and ddm[(v, "dev")] < ddm[("base", "dev")])
    okg &= q["Q2_P1_P2_calmar_up"] == bool(cal[(v, "P1")] > cal[("base", "P1")] and cal[(v, "P2")] > cal[("base", "P2")])
    okg &= q["Q3_random_regime_p95"] == bool(cal[(v, "dev")] > np.percentile(RN[RN.variant == v].calmar, 95))
    okg &= q["Q5_2018_19"] == bool(cl["g7"][v]["calmar"] > cl["g7"]["base"]["calmar"])
base_match = abs(cal[("base", "dev")] - c1["final_dev"]["calmar"]) < 1e-9 if c1["verdict"] == "N1 PASS" else True
ok("W4", okg and base_match, f"gate booleans re-derived from result files; N2 base dev Calmar == N1 FINAL dev Calmar: {base_match}")
# ---- W5 ----
proto = O_ / "N2_PROTOCOL_PREREGISTERED.md"
reg = [l.split(",") for l in (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().splitlines() if l.startswith("T16,")]
ok("W5", cl["protocol_sha"] == sha(proto) == (O_ / "N2_PROTOCOL_SHA256.txt").read_text().split()[0] and reg and reg[0][6] == sha(proto)
   and all(cl["files"][k] == sha(O_ / k) for k in cl["files"]) and cl["code_sha"] == sha(R_ / "src" / "research" / "n2_regime.py")
   and cl["n1_claims_sha"] == sha(O1 / "claims_n1.json"), "protocol lock, registry T16, file SHAs, code SHA, N1 claims SHA")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
