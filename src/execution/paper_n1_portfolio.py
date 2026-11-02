"""Forward PAPER recorder for the N1 portfolio: N1 FINAL K1 (4 sleeves, no signal stops) + N3 X2 spot/perp routing
(+ the T19 safety rule if adopted). Protocol: logs/paper_n1/PAPER_N1_PROTOCOL_PREREGISTERED.md.
PUBLIC Binance endpoints only: no keys, NO orders. One cycle per 4h close.
Amendment 1 (logs/paper_n1/PAPER_N1_AMENDMENT_1_PREREGISTERED.md): catch-up of missed cycles, D close without a price,
funding on the mark value, two-phase state/ledger write.
Amendment 2 (logs/paper_n1/PAPER_N1_AMENDMENT_2_PREREGISTERED.md): daily exchangeInfo check; inactive (spot not TRADING) and
perp_out (perp settled / delivery announced) coins get no opens and their positions are closed (live only, off in replay).
Usage:
  python paper_n1_portfolio.py --root data/paper_n1                       live: one cycle at the latest 4h boundary
  python paper_n1_portfolio.py --root <dir> --replay 2025-06-01 2025-10-01 replay from local research data (laptop only)
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src" / "research"))
from tf_edge_map import conditions                       # the verified TFX family definitions (no other research import)

CFG = json.loads((PROJ / "deploy" / "paper_n1_config.json").read_text())
CORE10 = CFG["core10"]
U2X = CFG["u2x"]
PERP = CFG["perp_names"]
RCOIN = {v: k for k, v in PERP.items()}                # replay only: research files are named by the spot symbol (SHIBUSDT, not 1000SHIBUSDT)
KHOLD = CFG["k_hold_hours"]                              # PIT medians from the backtest ledger, {"A|4h": hours, ...}
SAFETY = CFG["safety"]                                   # {"stop_pct": 0.35 or null, "coin_cap": 0.20 or null}
FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
TFH = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
FEE, FEE_SPOT, E0 = 0.00046, 0.00085, 10_000.0                     # fee amendment (logs/fees, 2d9d1485): BNB fee + impact; FEE was 0.00054
_FR = json.loads((PROJ / "deploy" / "fees.json").read_text())["rules"]
assert (FEE, FEE_SPOT) == (_FR["paper_futures_taker_per_side"], _FR["paper_spot_per_side"]), "fees differ from deploy/fees.json"
D_ANCHOR = pd.Timestamp("2020-02-01")
SPOT, FAPI = "https://api.binance.com", "https://fapi.binance.com"
H = pd.Timedelta(hours=1)
FAR_DELIVERY_MS = 4102444800000                          # 2100-01-01: an earlier perp deliveryDate = delisting announced (as ECO)


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- data sources ----------------
class Live:
    def __init__(self):
        self.n_req, self.errors = 0, []

    def get(self, base, path, **p):
        url = base + path + "?" + urllib.parse.urlencode(p)
        for k in range(4):
            try:
                self.n_req += 1
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "paper-n1"}), timeout=30) as r:
                    return json.loads(r.read().decode())
            except Exception as e:                                       # noqa: BLE001 - network: retry, then record
                if k == 3:
                    self.errors.append(f"{path} {p.get('symbol')}: {e}")
                    return None
                time.sleep(2 * (k + 1))

    def klines(self, sym, interval, T, n):
        step = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}[interval]
        end = int(T.timestamp() * 1000) + step - 1                         # include the bar that opens at T (its open = entry price)
        rows = []
        while len(rows) < n:
            k = self.get(SPOT, "/api/v3/klines", symbol=sym, interval=interval, endTime=end, limit=min(1000, n - len(rows)))
            if not k:
                break
            rows = k + rows
            end = k[0][0] - 1
            if len(k) < 1000:
                break
        if not rows:
            return None
        d = pd.DataFrame([r[:6] for r in rows], columns=["t", "open", "high", "low", "close", "volume"])
        d["t"] = pd.to_datetime(d.t, unit="ms")
        return d.drop_duplicates("t").set_index("t").astype(float).sort_index()

    def perp_daily_qv(self, perp, T):
        k = self.get(FAPI, "/fapi/v1/klines", symbol=perp, interval="1d", endTime=int(T.timestamp() * 1000) - 1, limit=40)
        if not k:
            return None
        return pd.Series([float(r[7]) for r in k], index=pd.to_datetime([r[0] for r in k], unit="ms"))

    def funding(self, perp, t0, t1):
        k = self.get(FAPI, "/fapi/v1/fundingRate", symbol=perp, startTime=int(t0.timestamp() * 1000), endTime=int(t1.timestamp() * 1000), limit=1000)
        if not k:
            return []
        return [(pd.Timestamp(int(r["fundingTime"]), unit="ms"), float(r["fundingRate"])) for r in k]

    def listing(self):
        """amendment 2 §1: ({spot symbol: status}, {perp symbol: (status, deliveryDate)}) or None if either call failed."""
        s = self.get(SPOT, "/api/v3/exchangeInfo", permissions="SPOT")
        f = self.get(FAPI, "/fapi/v1/exchangeInfo")
        if not s or not f:
            return None
        return ({x["symbol"]: x["status"] for x in s["symbols"]},
                {x["symbol"]: (x["status"], x.get("deliveryDate")) for x in f["symbols"]})


class Replay:
    """historical data from the laptop research store (same sources as N1); returns exactly what Live would at cycle T."""
    def __init__(self):
        self.n_req, self.errors, self.h1, self.qv, self.fr, self.rs = 0, [], {}, {}, {}, {}

    def _h1(self, sym):
        if sym not in self.h1:
            f = PROJ / "data" / "derived" / "n1" / "bars1h" / f"{sym}.parquet"
            self.h1[sym] = pd.read_parquet(f) if f.exists() else None
        return self.h1[sym]

    def klines(self, sym, interval, T, n):
        key = (sym, interval)
        if key not in self.rs:
            h = self._h1(sym)
            if h is None:
                self.rs[key] = None
            else:
                rule = {"1h": "1h", "4h": "4h", "1d": "1D"}[interval]
                self.rs[key] = h if rule == "1h" else h.resample(rule, label="left", closed="left").agg(
                    {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        b = self.rs[key]
        if b is None:
            return None
        j = b.index.searchsorted(T, side="right")              # bars that START <= T (the bar at T supplies only its open)
        return b.iloc[max(0, j - n):j]

    def perp_daily_qv(self, perp, T):
        if perp not in self.qv:
            f = PROJ / "data" / "futures_um" / f"{RCOIN.get(perp, perp)}_perp_1h.csv.gz"
            if not f.exists():
                self.qv[perp] = None
            else:
                v = pd.read_csv(f, usecols=["timestamp", "quote_volume"], parse_dates=["timestamp"]).set_index("timestamp").quote_volume
                self.qv[perp] = v.resample("1D").sum(min_count=1)
        s = self.qv[perp]
        return None if s is None else s[s.index < T.floor("D")].iloc[-40:]

    def funding(self, perp, t0, t1):
        if perp not in self.fr:
            f = PROJ / "data" / "futures_um" / f"{RCOIN.get(perp, perp)}_funding.csv"
            self.fr[perp] = pd.read_csv(f, parse_dates=["time"]).sort_values("time") if f.exists() else None
        x = self.fr[perp]
        if x is None:
            return []
        x = x[(x.time >= t0) & (x.time <= t1)]
        return list(zip(x.time, x.funding_rate.astype(float)))


# ---------------- signals ----------------
def tf_bars(b4, b1d, tf, T):
    """closed TF bars (start + tf <= T) built like the research resample."""
    if tf == "1D":
        b = b1d
    elif tf == "4h":
        b = b4
    else:
        b = b4.resample(f"{TFH[tf]}h", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return b[b.index + pd.Timedelta(hours=TFH[tf]) <= T]


def state(b, fam, side):
    le, lx, se, sx = conditions(b, fam)
    en, ex = (le, lx) if side == 1 else (se, sx)
    ev = np.where(en.fillna(False).values, 1.0, np.where(ex.fillna(False).values, 0.0, np.nan))
    return pd.Series(ev).ffill().fillna(0.0).values


_LIQ = {}


def liquid_today(src, coin, T):
    key = (coin, T.floor("D"))
    if key not in _LIQ:
        _LIQ[key] = _liquid(src, coin, T)
    return _LIQ[key]


def _liquid(src, coin, T):
    p = PERP.get(coin)
    if not p:
        return False
    qv = src.perp_daily_qv(p, T)
    if qv is None or len(qv) == 0:
        return False
    day = T.floor("D")
    full = qv.reindex(pd.date_range(qv.index.min(), day - pd.Timedelta(days=1), freq="D"))
    w = full.iloc[-30:].dropna()
    return len(w) >= 20 and float(w.median()) >= 50e6


# ---------------- engine ----------------
def delisting(src, st, T, notes):
    """amendment 2 §1/§4: the inactive / perp_out lists, refreshed at the first cycle of each UTC day (live only)."""
    if not hasattr(src, "listing"):
        return set(), set(), "off"
    dl = st.setdefault("delist", dict(day=None, inactive=[], perp_out=[]))
    if dl["day"] != str(T.date()):
        r = src.listing()
        if r is None:
            notes.append(f"delisting: exchangeInfo unavailable, lists of {dl['day']} kept")
        else:
            sp, fp = r
            uni = sorted(set(CORE10) | set(U2X) | {k.split("|")[1] for k in st["pos"]})
            dl["inactive"] = [c for c in uni if sp.get(c) != "TRADING"]
            dl["perp_out"] = [c for c in uni if c not in dl["inactive"] and c in PERP
                              and not (fp.get(PERP[c], ("MISSING", None))[0] == "TRADING" and (fp[PERP[c]][1] or FAR_DELIVERY_MS) >= FAR_DELIVERY_MS)]
            dl["day"] = str(T.date())
    return set(dl["inactive"]), set(dl["perp_out"]), dl["day"]


def cycle(src, st, T, init=False):
    acts, notes = [], []
    if len(_LIQ) > 50_000:
        _LIQ.clear()
    month = T.strftime("%Y-%m")
    bars, cur_open = {}, {}
    inactive, perp_out, dl_day = delisting(src, st, T, notes)
    need = sorted((set(CORE10) | set(U2X) | {p.split("|")[1] for p in st["pos"]}) - inactive)
    for c in need:
        b4 = src.klines(c, "4h", T, 2000); b1 = src.klines(c, "1d", T, 1000)
        if b4 is None or b1 is None or T not in b4.index:
            continue
        cur_open[c] = float(b4.loc[T, "open"])
        bars[c] = (b4[b4.index < T], b1[b1.index + pd.Timedelta(days=1) <= T])
    # mark-to-market and funding since the last cycle
    last = pd.Timestamp(st["last_T"]) if st.get("last_T") else T - pd.Timedelta(hours=4)
    fund_paid = 0.0
    for k, p in st["pos"].items():
        c = k.split("|")[1]
        if p["venue"] == "perp":
            for ft, r in src.funding(PERP[c], last + pd.Timedelta(milliseconds=1), T):
                if ft > pd.Timestamp(p["t"]):
                    fund_paid += p["side"] * r * abs(p["units"]) * p["last_px"]      # amendment 1 §3: mark value
    st["cash"] -= fund_paid
    # safety S1: catastrophe stop on 1h bars since the last cycle
    if SAFETY.get("stop_pct"):
        for k in list(st["pos"]):
            p = st["pos"][k]
            if p["sleeve"] == "D":
                continue
            c = k.split("|")[1]
            h1 = src.klines(c, "1h", T, 12)
            if h1 is None:
                continue
            h1 = h1[(h1.index >= max(last, pd.Timestamp(p["t"]))) & (h1.index < T)]
            stp = p["entry"] * (1 - p["side"] * SAFETY["stop_pct"])
            hit = h1[(h1.low <= stp) if p["side"] == 1 else (h1.high >= stp)]
            if len(hit):
                o = float(hit.open.iloc[0]); px = min(o, stp) if p["side"] == 1 else max(o, stp)
                close_pos(st, k, px, str(hit.index[0]), "stop35", acts)
    # amendment 2 §2/§3: positions in inactive coins (at the last mark) and perp positions in perp_out coins (at the open)
    for k in list(st["pos"]):
        c, p = k.split("|")[1], st["pos"][k]
        if c in inactive or (c in perp_out and p["venue"] == "perp"):
            px = cur_open.get(c, p["last_px"])
            if c not in cur_open:
                notes.append(f"delist close {k}: no price at T, closed at its last mark {p['last_px']}")
            close_pos(st, k, px, str(T), "delist", acts)
    equity =st["cash"] + sum(p["units"] * (cur_open.get(k.split("|")[1], p["last_px"]) - p["entry"]) for k, p in st["pos"].items())
    for k, p in st["pos"].items():
        p["last_px"] = cur_open.get(k.split("|")[1], p["last_px"])
    if st.get("month") != month:
        st["month"], st["E_m"] = month, equity
    Em = st["E_m"]
    nliq = None
    # A/B/C sub-signals: only for TFs whose bar closed exactly at T
    tfs_now = [tf for tf in TFH if (T - pd.Timestamp("2020-01-01")) % pd.Timedelta(hours=TFH[tf]) == pd.Timedelta(0)]
    first_tf = {tf: tf not in st.setdefault("init_tfs", []) for tf in tfs_now}     # init = the first evaluation of each TF (CODE_NOTES 2)
    for sleeve, coins, fams, tfs, side in (("A", CORE10, (0, 1, 2, 3), ["4h", "8h", "12h", "1D"], 1), ("B", CORE10, (4,), ["8h", "12h", "1D"], 1),
                                           ("C", U2X, (0, 1, 2, 3), ["4h", "8h", "12h", "1D"], -1)):
        for c in coins:
            if c not in bars:
                continue
            for tf in [t for t in tfs if t in tfs_now]:
                b = tf_bars(*bars[c], tf, T)
                if len(b) < 60 or b.index[-1] + pd.Timedelta(hours=TFH[tf]) != T:
                    continue
                for fi in fams:
                    k = f"{sleeve}|{c}|{tf}|{fi}"
                    s = state(b, FAM[fi], side)
                    held = k in st["pos"]
                    tf_init = first_tf[tf]
                    if held and s[-1] == 0:
                        close_pos(st, k, cur_open[c], str(T), "signal", acts)
                    elif not held and s[-1] == 1 and (s[-2] == 0 or tf_init) and c not in perp_out:   # amendment 2 §3: no opens
                        if sleeve == "C":
                            if not liquid_today(src, c, T):
                                continue
                            if nliq is None:
                                nliq = sum(liquid_today(src, x, T) for x in U2X if x not in inactive and x not in perp_out)  # amendment 2 §2
                            w = 0.4 / (16 * max(10, nliq))
                        else:
                            w = 0.005 if sleeve == "A" else 0.4 / 30
                        venue = "perp"
                        if sleeve in "AB":
                            fr = [r for _, r in src.funding(PERP.get(c, c), T - pd.Timedelta(days=7), T - pd.Timedelta(milliseconds=1))] if PERP.get(c) else []
                            if fr and np.mean(fr) * KHOLD[f"{sleeve}|{tf}"] / 8.0 > 0.00062:
                                venue = "spot"
                        if SAFETY.get("coin_cap"):
                            net = sum(p["units"] * cur_open[c] for kk, p in st["pos"].items() if kk.split("|")[1] == c) / Em
                            bound = SAFETY["coin_cap"] - net if side == 1 else SAFETY["coin_cap"] + net
                            w = float(np.clip(min(w, bound), 0.0, w))
                        if w > 0:
                            open_pos(st, k, sleeve, side, cur_open[c], w * Em, venue, str(T), "init" if (tf_init and s[-2] == 1) else "signal", acts)
    st["init_tfs"] = sorted(set(st["init_tfs"]) | set(tfs_now))
    # D: XS momentum rebalance after the close of decision days (anchor 2020-02-01, every 5 days)
    if T == T.floor("D") and ((T - pd.Timedelta(days=1)) - D_ANCHOR).days % 5 == 0:
        mom = {}
        for c in U2X:
            if c not in bars:
                continue
            b1 = bars[c][1]
            if c in perp_out:                                              # amendment 2 §3: D is perp-only
                continue
            if len(b1) >= 25 and b1.index[-1] == T - pd.Timedelta(days=1) and liquid_today(src, c, T - pd.Timedelta(days=1)):
                mom[c] = float(b1.close.iloc[-1] / b1.close.iloc[-21] - 1)
        for k in [k for k in st["pos"] if k.startswith("D|")]:
            c = k.split("|")[1]
            if c not in cur_open:                                          # amendment 1 §2
                notes.append(f"D close {k}: no price at T, closed at its last mark {st['pos'][k]['last_px']}")
            close_pos(st, k, cur_open.get(c, st["pos"][k]["last_px"]), str(T), "rebalance", acts, fee=0.0)
        if len(mom) >= 10:
            srt = pd.Series(mom).sort_values()
            q = len(srt) // 5
            neww = {c: 1 / q for c in srt.index[-q:]} | {c: -1 / q for c in srt.index[:q]}
            prev = st.get("d_w", {})
            turn = sum(abs(neww.get(c, 0) - prev.get(c, 0)) for c in set(neww) | set(prev))
            st["cash"] -= 0.2 * FEE * turn * Em
            st["d_w"] = neww
            for c, ww in neww.items():
                open_pos(st, f"D|{c}|1D|-1", "D", int(np.sign(ww)), cur_open[c], 0.2 * abs(ww) * Em, "perp", str(T), "rebalance", acts, fee=0.0)
        else:
            st["d_w"] = {}
            notes.append(f"D: only {len(mom)} eligible coins -> inactive")
    equity = st["cash"] + sum(p["units"] * (cur_open.get(k.split("|")[1], p["last_px"]) - p["entry"]) for k, p in st["pos"].items())
    gross = sum(abs(p["units"]) * cur_open.get(k.split("|")[1], p["last_px"]) for k, p in st["pos"].items())
    st["last_T"] = str(T)
    return dict(T=str(T), equity=equity, E_m=Em, funding_paid=fund_paid, n_pos=len(st["pos"]), gross=gross / equity if equity else None,
                actions=acts, notes=notes, data_errors=list(src.errors), n_requests=src.n_req, coins_with_data=len(bars),
                delisting="off" if dl_day == "off" else dict(day=dl_day, inactive=sorted(inactive), perp_out=sorted(perp_out)))


def open_pos(st, k, sleeve, side, px, notional, venue, t, why, acts, fee=None):
    fee = (FEE_SPOT if venue == "spot" else FEE) if fee is None else fee     # D legs: fee=0 (turnover cost booked separately)
    st["cash"] -= fee * notional
    st["pos"][k] = dict(sleeve=sleeve, side=side, entry=px, notional=notional, units=side * notional / px, venue=venue, t=t, last_px=px, fee=fee)
    acts.append(dict(a="open", k=k, side=side, px=px, notional=round(notional, 6), venue=venue, why=why))


def close_pos(st, k, px, t, why, acts, fee=None):
    p = st["pos"].pop(k)
    f = p["fee"] if fee is None else fee
    pnl = p["units"] * (px - p["entry"])
    st["cash"] += pnl - f * abs(p["units"]) * px
    acts.append(dict(a="close", k=k, px=px, entry=p["entry"], t_entry=p["t"], pnl=round(pnl, 6), why=why, venue=p["venue"]))


def fsync_write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text); fh.flush(); os.fsync(fh.fileno())


def recover_pending(root):
    """amendment 1 §4: a pending state whose last_T == the ledger's last T is completed, otherwise discarded."""
    pend, sf, lf = root / "state.json.pending", root / "state.json", root / "ledger.jsonl"
    if not pend.exists():
        return None
    ps = json.loads(pend.read_text())
    lastT = json.loads(lf.read_text().strip().splitlines()[-1])["T"] if lf.exists() and lf.stat().st_size else None
    if lastT is not None and str(ps.get("last_T")) == str(lastT):
        os.replace(pend, sf); return "rolled forward"
    pend.unlink(); return "discarded"


def missed_boundaries(last_T, T, cap=12):
    """amendment 1 §1: every 4 h boundary after last_T up to T (the latest cap of them)."""
    if last_T is None:
        return [T]
    ts = list(pd.date_range(pd.Timestamp(last_T) + pd.Timedelta(hours=4), T, freq="4h"))
    return ts[-cap:]


def run_cycle(root, src, T, init=False):
    root.mkdir(parents=True, exist_ok=True)
    sf, lf = root / "state.json", root / "ledger.jsonl"
    rp = recover_pending(root)
    if rp:
        print("pending state:", rp)
    st = json.loads(sf.read_text()) if sf.exists() else dict(cash=E0, pos={}, month=None, E_m=E0, last_T=None, d_w={})
    if st.get("last_T") and pd.Timestamp(st["last_T"]) >= T:
        return None                                                        # idempotent: this cycle is already recorded
    rec = cycle(src, st, T, init=init or not sf.exists())
    prev = lf.read_text().strip().splitlines()[-1] if lf.exists() and lf.stat().st_size else None
    rec["prev_sha256"] = json.loads(prev)["line_sha256"] if prev else "GENESIS"
    rec["code_sha256"] = sha_b(Path(__file__).read_bytes())
    rec["config_sha256"] = sha_b((PROJ / "deploy" / "paper_n1_config.json").read_bytes())
    body = json.dumps(rec, sort_keys=True, default=str)
    rec["line_sha256"] = sha_b(body.encode())
    pend = root / "state.json.pending"
    fsync_write(pend, json.dumps(st, indent=1, default=str))            # amendment 1 §4: phase 1
    with open(lf, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n"); fh.flush(); os.fsync(fh.fileno())
    os.replace(pend, sf)                                                # phase 2
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--replay", nargs=2)
    a = ap.parse_args()
    root = Path(a.root) if Path(a.root).is_absolute() else PROJ / a.root
    if a.replay:
        src = Replay()
        for T in pd.date_range(a.replay[0], a.replay[1], freq="4h", inclusive="left"):
            src.errors = []
            r = run_cycle(root, src, T)
            if r and T.hour == 0 and T.day == 1:
                print(T, round(r["equity"], 2), r["n_pos"], flush=True)
        return
    now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    T = now.floor("4h")
    if now - T < pd.Timedelta(minutes=3):
        T -= pd.Timedelta(hours=4)
    sf = root / "state.json"
    recover_pending(root) if root.exists() else None
    last_T = json.loads(sf.read_text()).get("last_T") if sf.exists() else None
    todo = missed_boundaries(last_T, T)
    if last_T is not None and len(todo) > 1:
        print(f"catch-up: {len(todo)} boundaries after {last_T}: {[str(t) for t in todo]}")
    for t in todo:
        src = Live()
        r = run_cycle(root, src, t)
        print("paper cycle", t, "skipped (already recorded)" if r is None else f"equity {r['equity']:.2f} pos {r['n_pos']} actions {len(r['actions'])} errors {len(r['data_errors'])}")


if __name__ == "__main__":
    main()
