"""
Step 8 information dashboard (NOT a trading rule). Builds dashboard/index.html from the live data that the Step 16 /
Step 16B loggers already keep (data/forward/live_1d, live_1h; logs/forward_multi_16b). Read only.
Per coin of the latest forward universe:
  - price, ATR % per timeframe and the "typical swing" (Phase 1 law: median swing ~ 5 ATR, ~2 ATR left after confirmation),
  - causal ZigZag (K = 3) state per timeframe and how far the current leg has moved since its pivot (in ATR),
  - nearest unbroken fractal support / resistance per timeframe (k = 3) and the volume share near the price,
  - the logged AI scores (D1 R5, 4H R6, 1h R24) and the paper portfolio.
Usage: python build_dashboard.py
"""
import sys
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "research", SRC / "analytics", SRC / "pipeline_1d", SRC / "execution"):
    sys.path.insert(0, str(p))
import swing_anatomy_phase1 as P
import swing_strategy_1d as E
import swing_study_1d as SS
from config import DATA_DIR, LOGS_DIR

ROOT = SRC.parent
LIVE1D, LIVE1H = DATA_DIR / "forward" / "live_1d", DATA_DIR / "forward" / "live_1h"
FM = LOGS_DIR / "forward_multi_16b"
OUTF = ROOT / "dashboard" / "index.html"
TFS = ["1W", "1D", "12h", "8h", "4h", "1h"]
TYPICAL = {"1W": 60.9, "1D": 30.1, "12h": 22.5, "8h": 17.8, "4h": 12.4, "1h": 6.2}     # Phase 1 median decline %, K = 3


def latest_pred_dir():
    for d in (FM / "predictions", FM / "test" / "predictions"):
        fs = sorted(d.glob("d1_*.csv")) if d.exists() else []
        if fs:
            return d, fs[-1].stem.split("_", 1)[1], d.parent.name == "test"
    return None, None, None


def coin_bars(s):
    h = pd.read_csv(LIVE1H / f"{s}_1h_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"],
                    parse_dates=["timestamp"]).sort_values("timestamp")
    h["timestamp"] = h.timestamp.dt.floor("h")
    h = h.drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    d = SS.load_1d(s, LIVE1D / f"{s}_1d.csv")[["timestamp", "open", "high", "low", "close"]]
    dq = h.set_index("timestamp").resample("1D").agg(dict(quote_volume="sum", taker_buy_quote="sum"))
    d = d.merge(dq, left_on="timestamp", right_index=True, how="left").fillna({"quote_volume": 0.0, "taker_buy_quote": 0.0})
    raw = {"1h": h, "4h": P.agg(h, "4h"), "8h": P.agg(h, "8h"), "12h": P.agg(h, "12h"), "1D": d, "1W": P.agg(d, "W-MON")}
    return {tf: P.clip_atr(x)[0] for tf, x in raw.items()}, h


def coin_row(s):
    bars, h = coin_bars(s)
    h1 = (h.timestamp.values, h.low.values, h.high.values, h.quote_volume.values)
    price = float(h.close.iloc[-1])
    row = dict(symbol=s, price=price, as_of=str(h.timestamp.iloc[-1] + pd.Timedelta(hours=1)))
    for tf in TFS:
        b = bars[tf]
        z = E.zz(b, 3.0)
        st = int(z["state"][-1])
        piv = [e for e in z["events"] if e["confirm_idx"] <= len(b) - 1]
        last = max(piv, key=lambda e: e["seq"]) if piv else None
        atr = float(b.ATR_14.iloc[-1])
        sup, res = P.sr_nearest(b)
        leg = np.nan
        if last is not None and np.isfinite(atr) and atr > 0:
            leg = (price - last["ref_price"]) / atr if "ref_price" in last else np.nan
        row[tf] = dict(state=st, atr_pct=atr / price * 100 if np.isfinite(atr) else np.nan, leg_atr=leg,
                       sup=sup[-1], res=res[-1],
                       vap=P.vap_at(h1, h.timestamp.values[-1] + np.timedelta64(1, "h"), price, 0.25 * atr, P.VAP_W[tf].to_timedelta64())
                       if np.isfinite(atr) else np.nan)
    return row


def fmt(x, nd=2, suf=""):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:,.{nd}f}{suf}"


def main():
    pdir, day, is_test = latest_pred_dir()
    assert pdir is not None, "no Step 16B prediction file yet"
    d1 = pd.read_csv(pdir / f"d1_{day}.csv")
    h4 = pd.read_csv(pdir / f"h4_r6_{day}.csv", parse_dates=["bar"])
    h1 = pd.read_csv(pdir / f"h1_r24_{day}.csv", parse_dates=["bar"])
    s4 = h4[h4.bar == h4.bar.max()].set_index("symbol").score
    s1 = h1[h1.bar == h1.bar.max()].set_index("symbol").score
    sd = d1.set_index("symbol").score
    syms = sorted(set(d1.symbol) | set(s4.index) | set(s1.index) | {"BTCUSDT"})
    rows = [coin_row(s) for s in syms]
    rank = lambda s: s.rank(ascending=False).astype(int).to_dict()
    r_d, r_4, r_1 = rank(sd), rank(s4), rank(s1)
    paper = None
    eqs = sorted((FM / "paper").glob("equity_*.csv")) if (FM / "paper").exists() else []
    if eqs:
        paper = pd.read_csv(eqs[-1])

    arrow = {1: '<span class="up">▲ ऊपर</span>', -1: '<span class="dn">▼ नीचे</span>', 0: "–"}
    th = "".join(f"<th>{tf}</th>" for tf in TFS)
    body = []
    for r in sorted(rows, key=lambda r: r_1.get(r["symbol"], 99)):
        s = r["symbol"]
        cells_state = "".join(f"<td>{arrow[r[tf]['state']]}<br><small>चाल {fmt(r[tf]['leg_atr'], 1)} ATR</small></td>" for tf in TFS)
        cells_lvl = "".join(
            f"<td><small>S {fmt((r['price'] / r[tf]['sup'] - 1) * 100 if np.isfinite(r[tf]['sup']) else np.nan, 1, '%')} नीचे<br>"
            f"R {fmt((r[tf]['res'] / r['price'] - 1) * 100 if np.isfinite(r[tf]['res']) else np.nan, 1, '%')} ऊपर<br>"
            f"VAP {fmt(r[tf]['vap'] * 100 if np.isfinite(r[tf]['vap']) else np.nan, 0, '%')}</small></td>" for tf in TFS)
        cells_atr = "".join(f"<td><small>ATR {fmt(r[tf]['atr_pct'], 2, '%')}<br>आम swing ~{fmt(5 * r[tf]['atr_pct'], 1, '%')}</small></td>" for tf in TFS)
        body.append(f"<tr><th rowspan=3>{html.escape(s)}<br><small>{fmt(r['price'], 4)}</small><br>"
                    f"<small>R24 #{r_1.get(s, '–')} · R6 #{r_4.get(s, '–')} · D1 #{r_d.get(s, '–')}</small></th>"
                    f"<td class=lab>दिशा (ZigZag K=3)</td>{cells_state}</tr>"
                    f"<tr><td class=lab>Support / Resistance</td>{cells_lvl}</tr><tr><td class=lab>हलचल</td>{cells_atr}</tr>")
    ptxt = "Paper portfolio अभी शुरू नहीं हुआ (पहला दिन: 2026-10-15)।"
    if paper is not None and len(paper):
        last = paper.iloc[-1]
        ptxt = (f"Paper portfolio M_AI3-50% ({html.escape(str(last['date']))[:10]}): <b>${last['M_AI3']:,.2f}</b> "
                f"(शुरुआत $10,000; D1 ${last.get('D1', np.nan):,.0f}, H4 ${last.get('H4', np.nan):,.0f}, H1 ${last.get('H1', np.nan):,.0f})")
    typical = " · ".join(f"{tf}: ~{v}%" for tf, v in TYPICAL.items())
    page = f"""<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crypto Market Map</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#ddd;--up:#0a7a3d;--dn:#b3261e;--card:#f6f7f9}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#111;--fg:#eee;--mut:#aaa;--line:#333;--up:#4cc38a;--dn:#ff6b6b;--card:#1b1d21}}}}
:root[data-theme=dark]{{--bg:#111;--fg:#eee;--mut:#aaa;--line:#333;--up:#4cc38a;--dn:#ff6b6b;--card:#1b1d21}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;margin:0;padding:16px}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;font-size:13px;min-width:900px}}
td,th{{border:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:left}} .lab{{color:var(--mut);white-space:nowrap}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}} .card{{background:var(--card);padding:10px 12px;border-radius:8px;margin:8px 0}} small{{color:var(--mut)}}
</style></head><body>
<h1>Crypto market map</h1>
<div class=card><b>सिर्फ जानकारी, trading का नियम नहीं।</b> Data: {html.escape(day)} {'(technical test day)' if is_test else ''}; candles तक: {html.escape(rows[0]['as_of'])} UTC.</div>
<div class=card>{ptxt}</div>
<div class=card><b>सबूत से साबित:</b> बड़े coins में "अगले 1 दिन में कौन आगे" (R24/R6 AUC ~0.565, 2018–19 पर 0.546)।
<b>साबित नहीं:</b> छोटे timeframe पर दिशा; support पर खरीदना; गिरावट का अनुमान।<br>
<b>Swing का गणित (Phase 1):</b> आम swing ≈ 5 ATR; पक्का होने तक ~57% हो चुका, आम तौर पर ~2 ATR बाकी। आम गिरावट: {typical}।<br>
<small>"चाल" = पिछले पक्के pivot से अब तक, ATR में। S/R = सबसे पास का न टूटा fractal level (k=3)। VAP = ±0.25 ATR में volume का हिस्सा। Rank = AI score का क्रम (1 = सबसे ऊपर)।</small></div>
<div class=wrap><table><tr><th>Coin</th><th></th>{th}</tr>{''.join(body)}</table></div>
</body></html>"""
    OUTF.parent.mkdir(parents=True, exist_ok=True)
    OUTF.write_text(page, encoding="utf-8")
    print(f"dashboard written: {OUTF} ({len(rows)} coins, data day {day})")


if __name__ == "__main__":
    main()
