"""
Audit (2026-10-15): are the stored research predictions of the brains free of look-ahead? (no new claims, checks only)
A  feature truncation, R6 (4h) and R24 (1h): for 40 random stored test rows each, the per-coin features are rebuilt from
   the raw 1h file CUT at the end of that bar (BTC file cut the same way) and compared with the features from the full
   file. Any difference = a feature that looks into the future.
B  month re-train from scratch on an OLD month (2022-06), R6 and R24: rows built with the research code, training rows
   chosen here by the rule "label known before the month start" (independently re-checked: known = open time of bar
   t+1+h, so known > bar), model fitted, June-2022 predictions compared with the stored research predictions.
C  D1: the production D1 scores (Step 19 U_AI_predictions) compared with Step 15 R5_AI predictions on common rows, so
   that the existing Step 15 replay (data cut at the as-of day + month model from scratch) also covers them;
   then that replay is run for an OLD day (2022-06-15) and a recent day (2026-09-15).
Usage: python audit_brains_noleak.py A|B|C
"""
import sys
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step19_large_caps_1d as S19
import step23_4h_brain as S23
import step24_1h_brain as S24
import s2_bear_training as S2

BASE = {"R6": [c for c in S23.BASE], "R24": [c for c in S24.BASE]}


def cut_bars(mod, path, t_end, tmp):
    h = pd.read_csv(path, parse_dates=["timestamp"])
    h = h[h.timestamp < t_end]
    q = Path(tmp) / Path(path).name
    h.to_csv(q, index=False)
    return (S23.bars_4h if mod is S23 else S24.bars_1h)(q)


def part_a():
    for name, mod, f, col, L in (("R6", S23, S23.OUT / "test_predictions_4h.csv", "R6_AI", pd.Timedelta(hours=4)),
                                 ("R24", S24, S24.OUT / "test_predictions_1h.csv", "R24_AI", pd.Timedelta(hours=1))):
        d = pd.read_csv(f, usecols=["symbol", "bar", col], parse_dates=["bar"])
        smp = d.sample(40, random_state=31)
        bars = S23.bars_4h if mod is S23 else S24.bars_1h
        btc_full = bars(S23.UNI1H / "BTCUSDT_1h_full.csv.gz").close
        worst, n = 0.0, 0
        with tempfile.TemporaryDirectory() as tmp:
            for r in smp.itertuples():
                t_end = r.bar + L
                full = mod.features(bars(S23.UNI1H / f"{r.symbol}_1h_full.csv.gz"), btc_full).loc[r.bar, BASE[name]]
                btc_cut = cut_bars(mod, S23.UNI1H / "BTCUSDT_1h_full.csv.gz", t_end, tmp).close
                cut = mod.features(cut_bars(mod, S23.UNI1H / f"{r.symbol}_1h_full.csv.gz", t_end, tmp), btc_cut).loc[r.bar, BASE[name]]
                a, b = full.values.astype(float), cut.values.astype(float)
                same = (np.isnan(a) == np.isnan(b)).all() and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=1e-12, atol=1e-12)
                assert same, (name, r.symbol, r.bar, [(c, x, y) for c, x, y in zip(BASE[name], a, b) if not (x == y or (np.isnan(x) and np.isnan(y)))])
                worst = max(worst, float(np.nanmax(np.abs(a - b))) if np.isfinite(a - b).any() else 0.0)
                n += 1
        print(f"[A PASS] {name}: {n} stored test rows; all {len(BASE[name])} per-coin features identical when the raw files are cut "
              f"at the bar end (max |diff| {worst:.1e}) -> no feature looks into the future")


def part_b():
    T = pd.Timestamp("2022-06-01")
    A, B = S2.split_sets()
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S23.UNI1H, S23.END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    for name, mod, f, col, lab, known, h, kw in (
            ("R6", S23, S23.OUT / "test_predictions_4h.csv", "R6_AI", "label6", "known6", pd.Timedelta(hours=4) * 7, {}),
            ("R24", S24, S24.OUT / "test_predictions_1h.csv", "R24_AI", "label24", "known24", pd.Timedelta(hours=1) * 25,
             dict(hour_filter=dict(train=lambda hr: hr % 3 == 0)))):
        Utr = S23.daily_members(data, last, list(data_k) + sorted(A & set(data)), S23.T_SIZE, pd.Timestamp("2020-01-01"), S23.END - pd.Timedelta(days=1))
        Ute = S23.daily_members(data, last, list(data_k) + sorted(B & set(data)), S23.U_SIZE, S23.START - pd.Timedelta(days=1), S23.END - pd.Timedelta(days=1))
        bars = S23.bars_4h if mod is S23 else S24.bars_1h
        R, _, _ = mod.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, bars(S23.UNI1H / "BTCUSDT_1h_full.csv.gz").close, **kw)
        TR, TE = R["train"], R["test"]
        k = TR[known].notna()
        assert (TR.loc[k, known] >= TR.loc[k, "bar"] + h).all(), f"{name}: a label is 'known' too early"
        tr = TR[(TR[known] < T) & TR[lab].notna()]
        assert (tr.bar < T).all() and (tr[known] < T).all()
        m = mod.fit(tr[mod.FEATS].values, tr[lab].values.astype(int)) if hasattr(mod, "fit") else S23.fit(tr[mod.FEATS].values, tr[lab].values.astype(int))
        te = TE[(TE.bar >= T) & (TE.bar < T + pd.offsets.MonthBegin(1))]
        p = m.predict_proba(te[mod.FEATS].values)[:, 1]
        ref = pd.read_csv(f, usecols=["symbol", "bar", col], parse_dates=["bar"])
        j = te[["symbol", "bar"]].assign(p=p).merge(ref, on=["symbol", "bar"], how="inner")
        assert len(j) == len(te), (name, len(j), len(te))
        diff = float(np.abs(j.p - j[col]).max())
        assert diff < 1e-12, (name, diff)
        print(f"[B PASS] {name}: June-2022 model re-trained from scratch on {len(tr)} rows (all labels known before 2022-06-01; "
              f"'known' >= bar + {h}); {len(j)} predictions equal the stored research ones (max |diff| {diff:.1e})")
        del R, TR, TE


def part_c():
    u = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    r5 = pd.read_csv(S15.OUT / "R5_AI_test_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    j = u.merge(r5, on=["symbol", "date"], suffixes=("_u", "_r5"))
    d = float(np.abs(j.score_u - j.score_r5).max())
    print(f"[C1] Step 19 U rows {len(u)}, common with Step 15 R5 {len(j)}, max |diff| on common rows {d:.1e}")
    for day in ("2022-06-15", "2026-09-15"):
        r = subprocess.run([sys.executable, str(SRC / "audits" / "replay_r5_vs_step15.py"), day], capture_output=True, text=True)
        print(r.stdout.strip()[-400:], r.stderr.strip()[-600:])
        assert r.returncode == 0, day


if __name__ == "__main__":
    {"A": part_a, "B": part_b, "C": part_c}[sys.argv[1]]()
