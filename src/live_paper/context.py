"""LIVE-AI context engine (2026-10-29): one structured snapshot of EVERYTHING the decision layer looks at, from live public sources
(read-only). Written as JSON (sha256) to logs/live_paper_lpt1_2026_10_29/context/ and printed as a compact brief.
Blocks (each one fails soft: a source that does not answer is recorded as missing, never invented):
  macro      ForexFactory weekly calendar (nfs.faireconomy.media): next / last high-impact USD (and all-currency) events, minutes to them,
             BLACKOUT flag = a high-impact USD event within -30..+30 min (desk playbook rule)
  cross      Yahoo chart API: S&P 500, Nasdaq-100 futures, US dollar index, US 10y yield, gold - last, change today, change 5 days
  crypto     CoinGecko global (total market cap 24h change, BTC dominance), alternative.me Fear & Greed (today, yesterday, 7 days ago)
  news       CoinDesk + Cointelegraph RSS and Bybit announcements of the last 12 h, with a keyword tag (the AI reads the headlines itself)
  coins      per symbol and timeframe (5m 15m 1h 4h 1d): trend (EMA20 vs EMA50), RSI14, ATR %, distance to VWAP / prior-day high-low,
             volume ratio, taker-buy share; futures context (funding, OI change 1h / 24h, long-short ratio) from Bybit
  regime     a rule label per symbol (TREND_UP / TREND_DOWN / RANGE, LOW / NORMAL / HIGH vol), written down so the AI cannot quietly redefine it
  forecasts  PRED-1: the latest forecasts and the live verified skill so far (logs/.../pred1/metrics.csv)
  account    LPT-1 paper account: equity, today's P&L vs the start of the day, open positions
Usage: python src/live_paper/context.py [--syms BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT]"""
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402

OUT = lpt.LOG / "context"
UA = {"User-Agent": "Mozilla/5.0 (research; read-only)"}
KEYS = {"risk_off": r"\b(hack|hacked|exploit|breach|lawsuit|sues|charged|ban|bans|banned|crackdown|liquidat\w*|outflows?|delist\w*|halts?|bankrupt\w*|collapse\w*|sell-?off|plunge\w*|crash\w*|insolven\w*|frozen|freeze|stolen|drain\w*)\b",
        "risk_on": r"\b(approv\w*|inflows?|record high|all-time high|ath|rally|rallies|surge\w*|adopt\w*|etf launch|rate cut|stimulus)\b",
        "macro": r"\b(fed|fomc|powell|cpi|inflation|gdp|pce|jobs|payrolls?|tariffs?|treasury|yields?|rates?|boj|ecb)\b",
        "regulation": r"\b(sec|cftc|regulat\w*|bill|congress|law|licen[cs]e)\b"}


def safe(fn):
    try:
        return fn()
    except Exception as e:                                                   # noqa: BLE001
        return {"missing": f"{type(e).__name__}: {str(e)[:100]}"}


def macro_block():
    d = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15, headers=UA).json()
    now = pd.Timestamp.now(tz="UTC")
    ev = []
    for x in d:
        t = pd.Timestamp(x["date"]).tz_convert("UTC")
        ev.append(dict(utc=t.isoformat(), minutes=round((t - now).total_seconds() / 60), country=x["country"], impact=x["impact"], title=x["title"],
                       forecast=x.get("forecast", ""), previous=x.get("previous", "")))
    hi = [e for e in ev if e["impact"] == "High"]
    usd = [e for e in hi if e["country"] == "USD"]
    nxt = [e for e in hi if e["minutes"] >= 0][:5]
    last = [e for e in hi if e["minutes"] < 0][-3:]
    black = [e for e in usd if -30 <= e["minutes"] <= 30]
    return dict(next_high=nxt, last_high=last, blackout=bool(black), blackout_events=black,
                usd_high_next=[e for e in usd if e["minutes"] >= 0][:3])


def cross_block():
    out = {}
    for name, sym in (("SP500", "^GSPC"), ("NQ_fut", "NQ=F"), ("DXY", "DX-Y.NYB"), ("US10Y", "^TNX"), ("Gold", "GC=F")):
        def one(sym=sym):
            j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params=dict(interval="1d", range="10d"),
                             timeout=12, headers=UA).json()["chart"]["result"][0]
            m = j["meta"]
            c = [x for x in j["indicators"]["quote"][0]["close"] if x is not None]
            last = m.get("regularMarketPrice", c[-1])
            prev = m.get("chartPreviousClose") if len(c) < 2 else c[-2]
            return dict(last=last, chg_1d=last / prev - 1 if prev else None, chg_5d=last / c[-6] - 1 if len(c) >= 6 else None,
                        market_time=datetime.fromtimestamp(m.get("regularMarketTime", 0), tz=timezone.utc).isoformat())
        out[name] = safe(one)
    return out


def crypto_block():
    g = safe(lambda: requests.get("https://api.coingecko.com/api/v3/global", timeout=12, headers=UA).json()["data"])
    f = safe(lambda: requests.get("https://api.alternative.me/fng/", params=dict(limit=8), timeout=12, headers=UA).json()["data"])
    out = {}
    if "missing" not in g:
        out.update(total_mcap_usd=g["total_market_cap"]["usd"], mcap_chg_24h=g["market_cap_change_percentage_24h_usd"] / 100,
                   btc_dominance=g["market_cap_percentage"]["btc"] / 100, eth_dominance=g["market_cap_percentage"]["eth"] / 100)
    else:
        out["global"] = g
    if isinstance(f, list):
        out.update(fear_greed=int(f[0]["value"]), fear_greed_label=f[0]["value_classification"], fear_greed_1d=int(f[1]["value"]),
                   fear_greed_7d=int(f[7]["value"]) if len(f) > 7 else None)
    else:
        out["fear_greed"] = f
    return out


def news_block(hours=24):
    items = []
    now = pd.Timestamp.now(tz="UTC")
    for src, url in (("coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"), ("cointelegraph", "https://cointelegraph.com/rss")):
        def rss(url=url, src=src):
            root = ET.fromstring(requests.get(url, timeout=12, headers=UA).content)
            for it in root.iter("item"):
                t = pd.Timestamp(it.findtext("pubDate")).tz_convert("UTC")
                if (now - t).total_seconds() <= hours * 3600:
                    items.append(dict(src=src, utc=t.isoformat(), title=(it.findtext("title") or "").strip()))
            return True
        r = safe(rss)
        if r is not True:
            items.append(dict(src=src, missing=r["missing"]))
    def byb():
        for x in requests.get("https://api.bybit.com/v5/announcements/index", params=dict(locale="en-US", limit=20), timeout=12).json()["result"]["list"]:
            t = pd.Timestamp(int(x["publishTime"]), unit="ms", tz="UTC")
            if (now - t).total_seconds() <= hours * 3600:
                items.append(dict(src="bybit", utc=t.isoformat(), title=x["title"], type=x.get("type", {}).get("title", "")))
        return True
    safe(byb)
    for it in items:
        if "title" in it:
            low = it["title"].lower()
            it["tags"] = [k for k, rx in KEYS.items() if re.search(rx, low)]
    items.sort(key=lambda x: x.get("utc", ""), reverse=True)
    tags = pd.Series([t for it in items for t in it.get("tags", [])]).value_counts().to_dict() if items else {}
    return dict(hours=hours, n=len([i for i in items if "title" in i]), tag_counts=tags, items=items[:40])


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def tf_state(k):
    c = k.c.values
    pc = k.c.shift(1)
    tr = pd.concat([k.h - k.l, (k.h - pc).abs(), (k.l - pc).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1] / c[-1])
    d = np.diff(c)
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    e20, e50 = ema(c, 20)[-1], ema(c, 50)[-1]
    vr = float(k.qv.iloc[-1] / max(k.qv.iloc[-21:-1].mean(), 1e-9))
    tb = float(k.tbq.iloc[-1] / max(k.qv.iloc[-1], 1e-9)) if "tbq" in k else None
    return dict(close=float(c[-1]), trend=int(np.sign(e20 - e50)), ema20_dist=float(c[-1] / e20 - 1), rsi=float(100 - 100 / (1 + up / max(dn, 1e-12))),
                atr_pct=atr, ret_1=float(c[-1] / c[-2] - 1), ret_10=float(c[-1] / c[-11] - 1), vol_ratio=vr, taker_buy=tb)


def coin_block(sym):
    out = {}
    for tf in ("5m", "15m", "1h", "4h", "1d"):
        k = lpt.klines("spot", sym, tf, 300).iloc[:-1]                          # closed bars only
        out[tf] = tf_state(k)
    m5 = lpt.klines("spot", sym, "5m", 400)
    day0 = lpt.now_ms() // 86_400_000 * 86_400_000
    t = m5[m5.t >= day0]
    d1 = lpt.klines("spot", sym, "1d", 3)
    p = float(m5.c.iloc[-1])
    out["levels"] = dict(price=p, vwap_dist=p / (t.qv.sum() / t.v.sum()) - 1 if t.v.sum() else None, pdh_dist=p / float(d1.h.iloc[-2]) - 1,
                         pdl_dist=p / float(d1.l.iloc[-2]) - 1, day_high=float(t.h.max()) if len(t) else None, day_low=float(t.l.min()) if len(t) else None)
    def fut():
        tk = requests.get(f"{lpt.BYB}/tickers", params=dict(category="linear", symbol=sym), timeout=8).json()["result"]["list"][0]
        oi = requests.get(f"{lpt.BYB}/open-interest", params=dict(category="linear", symbol=sym, intervalTime="1h", limit=25), timeout=8).json()["result"]["list"]
        o = [float(x["openInterest"]) for x in oi]
        ls = requests.get(f"{lpt.BYB}/account-ratio", params=dict(category="linear", symbol=sym, period="1h", limit=1), timeout=8).json()["result"]["list"][0]
        return dict(funding=float(tk["fundingRate"]), basis_bps=(float(tk["lastPrice"]) / p - 1) * 1e4, oi_chg_1h=o[0] / o[1] - 1, oi_chg_24h=o[0] / o[-1] - 1,
                    long_short_buy_ratio=float(ls["buyRatio"]))
    out["futures"] = safe(fut)
    tr1h, tr4h, tr1d = out["1h"]["trend"], out["4h"]["trend"], out["1d"]["trend"]
    a1h = out["1h"]["atr_pct"]
    trend = "TREND_UP" if tr1h > 0 and tr4h > 0 else "TREND_DOWN" if tr1h < 0 and tr4h < 0 else "RANGE"
    vol = "LOW_VOL" if a1h < 0.004 else "HIGH_VOL" if a1h > 0.012 else "NORMAL_VOL"
    out["regime"] = dict(label=f"{trend}/{vol}", daily_trend=tr1d,
                         rule="TREND_* = 1h and 4h EMA20-vs-EMA50 agree; vol by ATR1h % (<0.4 % low, >1.2 % high)")
    return out


def forecast_block():
    f = lpt.LOG / "pred1" / "metrics.csv"
    if not f.exists():
        return {"missing": "no PRED-1 metrics yet"}
    M = pd.read_csv(f)
    best = M[M.model != "M0_naive"].sort_values("skill_vs_M0", ascending=False).groupby("tf").head(1)
    return dict(useful_models=int(M.USEFUL.sum()), best_by_tf=best[["tf", "model", "h", "n", "skill_vs_M0", "dir_hit", "dm_q", "fee_hurdle"]].round(4).to_dict("records"),
                note="USEFUL requires n>=300, skill>0, BH-adjusted DM q<=0.05 and direction above the fee hurdle (PRED-1 protocol 5)")


def account_block():
    s = lpt.load_state()
    return dict(cash=s["cash"], day=s.get("day"), day_start_equity=s.get("day_start_equity"), realized=s["realized"], fees=s["fees"],
                open_positions=list(s["positions"].values()), halted_day=s.get("halted_day"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syms", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t = lpt.now_ms()
    ctx = dict(utc=lpt.iso(t), macro=safe(macro_block), cross=safe(cross_block), crypto=safe(crypto_block), news=safe(news_block),
               coins={s: safe(lambda s=s: coin_block(s)) for s in a.syms.split(",")}, forecasts=safe(forecast_block), account=safe(account_block))
    raw = json.dumps(ctx, sort_keys=True, default=str).encode()
    h = hashlib.sha256(raw).hexdigest()
    (OUT / f"{lpt.iso(t).replace(':', '').replace('-', '')}_{h[:12]}.json").write_bytes(raw)
    lpt.append_chain(lpt.LOG / "contexts.jsonl", dict(utc=ctx["utc"], sha=h))
    # compact brief
    m = ctx["macro"]
    print(f"CONTEXT {ctx['utc']} sha {h}")
    if "missing" not in m:
        print(f" MACRO blackout={m['blackout']} next high: " + "; ".join(f"{e['country']} {e['title']} in {e['minutes']} min" for e in m["next_high"][:3]))
    print(" CROSS " + "  ".join(f"{k} {v.get('last'):.4g} ({100 * (v.get('chg_1d') or 0):+.2f}% 1d)" for k, v in ctx["cross"].items() if "last" in v))
    c = ctx["crypto"]
    print(f" CRYPTO mcap 24h {100 * c.get('mcap_chg_24h', 0):+.2f}%  BTC dom {100 * c.get('btc_dominance', 0):.1f}%  Fear&Greed {c.get('fear_greed')} "
          f"({c.get('fear_greed_label')}) 1d {c.get('fear_greed_1d')} 7d {c.get('fear_greed_7d')}")
    n = ctx["news"]
    if "missing" not in n:
        print(f" NEWS last {n['hours']} h: {n['n']} items, tags {n['tag_counts']}")
        tit = [i for i in n["items"] if "title" in i]
        exch = re.compile(r"(binance|bybit|okx|coinbase|kraken|bitget|tether|circle)", re.I)
        alert = [i for i in tit if "risk_off" in i.get("tags", []) or exch.search(i["title"])]
        for it in alert:                                                     # every risk-off / exchange headline first (journal 30 Oct)
            print(f" ! {it['utc'][5:16]} {it['src']:13s} {it['title'][:110]}  {it.get('tags', [])}")
        for it in [i for i in tit if i not in alert][:6]:
            print(f"   {it['utc'][11:16]} {it['src']:13s} {it['title'][:110]}  {it.get('tags', [])}")
    for s, v in ctx["coins"].items():
        if "missing" in v:
            print(f" {s} missing {v['missing']}"); continue
        lv, fu = v["levels"], v["futures"]
        tfs = " ".join(f"{tf}:{'+' if v[tf]['trend'] > 0 else '-'}{v[tf]['rsi']:.0f}/{100 * v[tf]['atr_pct']:.2f}%" for tf in ("5m", "15m", "1h", "4h", "1d"))
        ff = "" if "missing" in fu else f" fund {100 * fu['funding']:.4f}% OI1h {100 * fu['oi_chg_1h']:+.2f}% OI24h {100 * fu['oi_chg_24h']:+.2f}% L/S {fu['long_short_buy_ratio']:.2f}"
        print(f" {s:8s} {lv['price']:.6g} {v['regime']['label']:22s} vwap {100 * (lv['vwap_dist'] or 0):+.2f}% pdh {100 * lv['pdh_dist']:+.2f}% pdl {100 * lv['pdl_dist']:+.2f}% | {tfs} |{ff}")
    f = ctx["forecasts"]
    print(f" FORECASTS {f if 'missing' in f else 'useful models: ' + str(f['useful_models'])}")
    ac = ctx["account"]
    print(f" ACCOUNT cash {ac.get('cash')} open {len(ac.get('open_positions', []))} day start {ac.get('day_start_equity')}")


if __name__ == "__main__":
    main()
