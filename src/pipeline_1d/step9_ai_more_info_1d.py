"""
Step 9: Step 8 AI test repeated with MORE INFORMATION (order flow + intraday structure from verified 1h klines).
Protocol: logs/strategy_1d_step9_ai/STEP9_PROTOCOL_PREREGISTERED.md (SHA256 in PROTOCOL_SHA256.txt).
Everything except the feature list is the Step 8 code (imported, not copied).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_strategy_1d as E
import step7_swing_ai_1d as S7
import step8_ai_entry_exit_1d as S8
from step6_4_survivorship_1d import load_all, universe
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step9_ai"
H1 = DATA_DIR / "raw_1h_full"
NEW = ["taker_buy_ratio", "taker_ratio_5d", "taker_ratio_chg", "taker_ratio_last4h", "trades_ratio30",
       "trade_size_ratio30", "close_pos_range", "last4h_ret", "last4h_vol_share", "hourly_ret_std",
       "intraday_maxdd", "hour_of_high", "hour_of_low"]


def hourly_daily_features(sym, d1):
    """Per-day features from the coin's 24 hourly candles + cross-check against the verified 1D candle."""
    h = pd.read_csv(H1 / f"{sym}_1h_full.csv.gz", parse_dates=["timestamp"])
    h["day"] = h.timestamp.dt.normalize()
    h["hour"] = h.timestamp.dt.hour
    h["ret"] = h.close.pct_change()
    g = h.groupby("day")
    agg = pd.DataFrame(dict(o=g.open.first(), hi=g.high.max(), lo=g.low.min(), c=g.close.last(), v=g.volume.sum(),
                            n=g.size(), trades=g.trades.sum(), qv=g.quote_volume.sum(), tb=g.taker_buy_base.sum()))
    last4 = h[h.hour >= 20].groupby("day")
    agg["v4"] = last4.volume.sum()
    agg["tb4"] = last4.taker_buy_base.sum()
    c19 = h[h.hour == 19].set_index("day").close
    agg["c19"] = c19
    agg["ret_std"] = g.ret.std()
    agg["hour_hi"] = h.loc[g.high.idxmax(), ["day", "hour"]].set_index("day").hour
    agg["hour_lo"] = h.loc[g.low.idxmin(), ["day", "hour"]].set_index("day").hour
    h["runmax"] = g.high.cummax()
    h["dd"] = h.low / h.runmax - 1
    agg["maxdd"] = h.groupby("day").dd.min()
    # cross-check with the verified 1D file (evidence check on the evidence data)
    d = d1.set_index("timestamp")[["open", "high", "low", "close", "volume"]].join(agg, how="left")
    ok = (np.isclose(d.o, d.open, rtol=1e-9) & np.isclose(d.hi, d.high, rtol=1e-9) & np.isclose(d.lo, d.low, rtol=1e-9)
          & np.isclose(d.c, d.close, rtol=1e-9) & np.isclose(d.v, d.volume, rtol=1e-6))
    ok = np.asarray(ok, dtype=bool)
    f = pd.DataFrame(index=d.index)
    f["taker_buy_ratio"] = d.tb / d.v
    f["taker_ratio_5d"] = f.taker_buy_ratio.rolling(5).mean()
    f["taker_ratio_chg"] = f.taker_buy_ratio - f.taker_ratio_5d
    f["taker_ratio_last4h"] = d.tb4 / d.v4
    f["trades_ratio30"] = d.trades / d.trades.rolling(30).mean()
    size = d.qv / d.trades
    f["trade_size_ratio30"] = size / size.rolling(30).mean()
    f["close_pos_range"] = (d.c - d.lo) / (d.hi - d.lo)
    f["last4h_ret"] = d.c / d.c19 - 1
    f["last4h_vol_share"] = d.v4 / d.v
    f["hourly_ret_std"] = d.ret_std
    f["intraday_maxdd"] = d.maxdd
    f["hour_of_high"] = d.hour_hi
    f["hour_of_low"] = d.hour_lo
    f = f.replace([np.inf, -np.inf], np.nan)
    f.loc[~ok] = np.nan                                       # never use a day that fails the cross-check
    stats = dict(days=int(len(d)), hourly_days=int(d.n.notna().sum()), matched=int(ok.sum()),
                 mismatched=int((d.n.notna().values & ~ok).sum()), no_hourly=int(d.n.isna().sum()),
                 days_with_24h=int((d.n == 24).sum()))
    return f.reset_index(drop=True), stats


def install_features(data, real_last):
    base_fn = S8.daily_features
    xstats = {}

    def daily_plus(data_):
        feats = base_fn(data_)
        for s, f in feats.items():
            real = data_[s][data_[s].timestamp <= real_last[s]]
            nf, st = hourly_daily_features(s, real)
            xstats[s] = st
            nf = nf.reindex(range(len(f)))                           # padded (delisted) days -> missing
            feats[s] = pd.concat([f, nf.set_index(f.index)], axis=1)
        return feats
    S8.DAILY = S8.DAILY + NEW
    S8.ENTRY_FEATURES = sorted(set(S7.FEATURES) | set(S8.DAILY))
    S8.EXIT_FEATURES = S8.EXIT_FEATURES + NEW
    S8.daily_features = daily_plus
    return xstats


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proto_hash = hashlib.sha256((OUT / "STEP9_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest()
    assert proto_hash == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    data, real_last = load_all()
    xstats = install_features(data, real_last)
    S8.OUT = OUT
    uni = universe(data, real_last)
    members = {(y, s) for y, m in zip(uni.year, uni.members) for s in m.split(";")}
    ent, ext = S8.build_sets(data, real_last, S8.daily_features(data))
    print(f"entry rows {len(ent)}, exit rows {len(ext)} in {time.time() - t0:.0f}s; 1h cross-check:", flush=True)
    xs = pd.DataFrame(xstats).T
    xs.to_csv(OUT / "hourly_vs_daily_crosscheck.csv")
    print(xs.to_string(), flush=True)
    ent["member"] = [(d.year, s) in members for s, d in zip(ent.symbol, ent.signal_date)]
    ext = ext.merge(ent[["cand_id", "member", "signal_date"]], on="cand_id", how="left")

    claims = dict(protocol_sha256=proto_hash, coins=len(data), entry_rows=int(len(ent)), exit_rows=int(len(ext)),
                  entry_features=len(S8.ENTRY_FEATURES), exit_features=len(S8.EXIT_FEATURES),
                  crosscheck=dict(matched=int(xs.matched.sum()), mismatched=int(xs.mismatched.sum()),
                                  no_hourly=int(xs.no_hourly.sum())))
    runs = {}
    for label, shuffle in (("AI", False), ("CONTROL_shuffled", True)):
        pe, px, log = S8.walk_forward(ent, ext, shuffle=shuffle)
        E_, X_ = ent.join(pe, how="inner"), ext.join(px, how="inner")
        E_["month"] = E_.signal_date.dt.to_period("M").astype(str)
        X_["month"] = X_.date.dt.to_period("M").astype(str)
        E_.to_csv(OUT / f"{label}_entry_predictions.csv", index=False)
        X_.to_csv(OUT / f"{label}_exit_predictions.csv", index=False)
        log.to_csv(OUT / f"{label}_training_log.csv", index=False)
        claims[f"{label}_entry_skill_members"] = S8.skill(E_[E_.member])
        claims[f"{label}_exit_skill_members"] = S8.skill(X_[X_.member == True])
        claims[f"{label}_entry_skill_allcoins"] = S8.skill(E_)
        runs[label] = (E_, X_)
        print(label, {k: round(v["auc"], 4) for k, v in claims.items() if k.startswith(label)}, flush=True)

    E_, X_ = runs["AI"]
    Ec, Xc = runs["CONTROL_shuffled"]
    port = {}
    for name, (en, ex, mode, aix) in {"BASELINE_all_swings": (E_, X_, "all", False),
                                      "AI_entry_only": (E_, X_, "ai", False),
                                      "AI_exit_only": (E_, X_, "all", True),
                                      "AI_full": (E_, X_, "ai", True),
                                      "CONTROL_full": (Ec, Xc, "ai", True)}.items():
        tr, eq, cash = S8.run_portfolio(data, en, ex, members, mode, aix)
        assert abs(E.INITIAL_CAPITAL + tr["pnl"].sum() - cash) < 1e-6
        tr.drop(columns=["plan"], errors="ignore").to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        port[name] = S7.summarize(tr, eq, cash, name)
        port[name]["exit_reasons"] = tr.exit_reason.value_counts().to_dict()
        print(name, {k: port[name][k] for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades")}, flush=True)
    claims["portfolio"] = port

    def gate_skill(k):
        a, c = claims[f"AI_{k}_skill_members"], claims[f"CONTROL_shuffled_{k}_skill_members"]
        return dict(auc_ge_055=a["auc"] >= 0.55, ci_low_gt_050=a["ci_low"] > 0.50, beats_control=a["auc"] > c["auc"],
                    top_q_gt_bottom_q=a["quintile_rates"][-1] > a["quintile_rates"][0])
    g1, g2 = gate_skill("entry"), gate_skill("exit")
    cal = {k: v["calmar"] for k, v in port.items()}
    g3_full = cal["AI_full"] > cal["BASELINE_all_swings"] and cal["AI_full"] > cal["CONTROL_full"]
    g3_entry = cal["AI_entry_only"] > cal["BASELINE_all_swings"] and cal["AI_entry_only"] > cal["CONTROL_full"]
    decision = ("DEPLOY_AI_FULL" if all(g1.values()) and all(g2.values()) and g3_full else
                "DEPLOY_AI_ENTRY_ONLY" if all(g1.values()) and g3_entry else "FAIL_NOTHING_DEPLOYED")
    claims["gates"] = dict(G1_entry=g1, G2_exit=g2, G3_full=g3_full, G3_entry_only=g3_entry, decision=decision)
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=float))
    print("\nGATES:", json.dumps(claims["gates"], indent=1, default=str), flush=True)


if __name__ == "__main__":
    main()
