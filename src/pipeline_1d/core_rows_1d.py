"""
Shared builder of the Step 13 "core" feature rows for ANY as-of date and ANY data folder (used by Step 15 research
and the Step 16 forward dry-run). It is a line-by-line copy of the data/feature part of step13_unseen_coins_1d.main
(Step 13 itself is not modified), with two generalisations:
  * all coins are read from one folder of <SYM>_1d.csv files (+ one folder of <SYM>_1h_full.csv.gz files),
  * everything is cut at `asof` (no row after it is read), delisted coins are padded only up to `asof`.
Equivalence with Step 13 is proven by `replay_check` (as-of 2026-09-15 must reproduce Step 13's p1 exactly).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_study_1d as SS
import step7_swing_ai_1d as S7
import step8_ai_entry_exit_1d as S8
import step9_ai_more_info_1d as S9
import step10_ai_1d as S10
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
from config import SYMBOLS

EXTENDED = ["LUNAUSDT", "FTTUSDT", "AVAXUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "FILUSDT", "ETCUSDT", "XLMUSDT",
            "TRXUSDT", "BCHUSDT", "EOSUSDT", "ICPUSDT", "AXSUSDT", "SANDUSDT", "ALGOUSDT", "VETUSDT", "THETAUSDT",
            "NEARUSDT", "SHIBUSDT"]
KNOWN = list(SYMBOLS) + sorted(EXTENDED)          # load_all order: config SYMBOLS, then raw_extended files sorted by name
F_CORE = None          # filled by build(): S8.DAILY (+1h) + btc state + breadth + Fear&Greed + 6 reference ranks
_INSTALLED = False
_REAL_LAST = {}        # the Step 9 wrapper keeps a reference to this dict; it is refreshed on every build()


def pad_to(df, real_last, asof):
    """Same rule as step6_4.load_all / S13.pad_to_end, but up to `asof`."""
    if real_last >= asof:
        return df
    pad_days = pd.date_range(real_last + pd.Timedelta(days=1), asof, freq="D")
    c = float(df["close"].iloc[-1])
    pad = pd.DataFrame(dict(timestamp=pad_days, open=c, high=c, low=c, close=c, volume=0.0))
    df = pd.concat([df[["timestamp", "open", "high", "low", "close", "volume"]], pad], ignore_index=True)
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()],
                   axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean()
    return df


def load_folder(dir_1d, dir_1h, asof):
    """Known 30 coins + every other coin passing the Step 13 selection rules, cut at `asof`."""
    data_k, last_k, data_n, last_n, log = {}, {}, {}, {}, []
    for f in sorted(Path(dir_1d).glob("*_1d.csv")):
        s = f.name.split("_")[0]
        why = None
        if s not in KNOWN:
            if s in S13.NOT_CRYPTO:
                why = "not a crypto asset"
            elif not (Path(dir_1h) / f"{s}_1h_full.csv.gz").exists():
                why = "no 1h file"
        if why is None:
            df = SS.load_1d(s, f)
            df = df[df.timestamp <= asof].reset_index(drop=True)
            if s not in KNOWN:
                if len(df) < S13.MIN_DAYS:
                    why = f"only {len(df)} days"
                elif df.close.pct_change().abs().median() < S13.PEG_MEDIAN_ABS_RET:
                    why = "pegged price"
            elif len(df) == 0:
                why = "known coin without data"
        if why:
            log.append(dict(symbol=s, used=False, reason=why))
            continue
        last = df.timestamp.max()
        if s in KNOWN:
            data_k[s], last_k[s] = pad_to(df, last, asof), last
        else:
            data_n[s], last_n[s] = pad_to(df, last, asof), last
        log.append(dict(symbol=s, used=True, known=s in KNOWN, last=last.date()))
    assert set(data_k) == set(KNOWN), set(KNOWN) - set(data_k)
    data_k = {s: data_k[s] for s in KNOWN}                     # Step 13 order (load_all: 10 SYMBOLS, then extended)
    return data_k, last_k, data_n, last_n, pd.DataFrame(log)


def build(data_k, last_k, data_n, last_n, dir_1h_known, dir_1h_new, asof, fng):
    """Pk (known rows, all), Pn (other coins, with `liquid`), feature list -- exactly the Step 13 construction."""
    global _INSTALLED, F_CORE
    for mod in (S7, S8, S13):
        mod.DATA_END = pd.Timestamp(asof)
    _REAL_LAST.clear()
    _REAL_LAST.update({**last_k, **last_n})
    if not _INSTALLED:                                  # install once: a second install would add the 1h columns twice
        S9.install_features({**data_k, **data_n}, _REAL_LAST)
        _INSTALLED = True
    S9.H1 = Path(dir_1h_known)
    feats_k = S8.daily_features(data_k)
    S9.H1 = Path(dir_1h_new)
    btc = {"BTCUSDT": data_k["BTCUSDT"]}
    feats_n = S8.daily_features({**btc, **data_n})
    feats_n.pop("BTCUSDT")
    S9.H1 = Path(dir_1h_known)
    br, _ = S13.reference_breadth(data_k)
    chk = feats_k["ETHUSDT"]["breadth_k3_up_t"].values
    assert np.allclose(chk.astype(float), data_k["ETHUSDT"].timestamp.map(br).values.astype(float), equal_nan=True)
    for s, f in feats_n.items():
        f["breadth_k3_up_t"] = data_n[s].timestamp.map(br).values
    Pk = S10.path2_rows(data_k, last_k, feats_k, set()).join(fng, on="date")
    Pn = S10.path2_rows(data_n, last_n, feats_n, set()).join(fng, on="date")
    for c in S13.RANK_CORE:
        Pk[f"xr_{c}"] = Pk.groupby("date")[c].rank(pct=True)
        Pn[f"xr_{c}"] = S13.rank_vs_reference(Pk[c].values, Pk.date.values, Pn[c].values, Pn.date.values)
    liq_n, liq_k = S13.liquid_flag(data_n, last_n), S13.liquid_flag(data_k, last_k)
    Pn["liquid"] = [bool(liq_n[s].get(d, False)) for s, d in zip(Pn.symbol, Pn.date)]
    Pk["liquid"] = [bool(liq_k[s].get(d, False)) for s, d in zip(Pk.symbol, Pk.date)]
    F_CORE = S8.DAILY + ["btc_k3_state_t", "breadth_k3_up_t"] + S11.FNG_COLS + [f"xr_{c}" for c in S13.RANK_CORE]
    assert not any(c in F_CORE for c in S10.FUT) and len(F_CORE) == 47
    return Pk, Pn, F_CORE


def fit_b1(Pk, F, month_start):
    """Step 13 B1 model for the month starting `month_start` (labels known strictly before it)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    T = pd.Timestamp(month_start)
    tr = Pk[(Pk.known_1 < T) & Pk.label_1.notna()]
    assert (tr.date < T).all()
    m = HistGradientBoostingClassifier(random_state=0, **S11.KW).fit(tr[F].values, tr.label_1.values.astype(int))
    return m, len(tr)
