"""E-3 replay (protocol §6), laptop. Hourly cycles at h:50, 2026-09-01 .. 2026-09-30, with the SAME cycle() as the VM;
producers from data/derived/eco/replay (built by eco_replay_build.py with the deployed producer code); fills by SimExchange
at the open of bar h+1. Usage: python src/eco/eco_replay.py <out_dir>"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C
import eco_exchange as X
import eco_orchestrator as O

PROJ = C.PROJ
RP = PROJ / "data" / "derived" / "eco" / "replay"
F4_AVAIL = pd.Timedelta(days=1, hours=2, minutes=15)        # F4 as-of d is written at d+1 02:15 UTC (cron 07:45 IST)
N1_AVAIL = pd.Timedelta(minutes=41)                         # PaperN1 cycle T runs at T + 41 min


class ReplayEnv:
    mode = "replay"

    def __init__(self, cfg):
        self.cfg = cfg
        self.sim = X.SimExchange(PROJ / "data" / "futures_um", fee=cfg["fee"])
        self.f4o = json.loads((RP / "f4_orders.json").read_text())
        self.n1L = [json.loads(l) for l in (RP / "n1" / "ledger.jsonl").read_text().splitlines() if l.strip()]
        self.n1T = [pd.Timestamp(r["T"]) for r in self.n1L]
        self.filt = X.parse_filters(json.loads((RP / "exchange_info.json").read_text(encoding="utf-8")))
        self.coin_of = {}
        self.now, self.last_error, self._px, self._pxa = None, None, {}, {}
        self._pos_cache = (-1, {})

    def notes(self):
        e, self.sim.errors = self.sim.errors, []
        return e

    def n1_positions(self, i):
        """rebuild the N1 book after ledger line i from the open / close actions (open_pos: units = side*notional/px)."""
        j0, pos = self._pos_cache if self._pos_cache[0] <= i else (-1, {})
        pos = dict(pos)
        for r in self.n1L[j0 + 1: i + 1]:
            for a in r["actions"]:
                if a["a"] == "open":
                    pos[a["k"]] = (a["k"].split("|")[1], int(a["side"]), abs(a["notional"] / a["px"]), a["venue"])
                else:
                    pos.pop(a["k"], None)
        self._pos_cache = (i, pos)
        return pos

    def n1(self, now):
        i = max((j for j, T in enumerate(self.n1T) if T + N1_AVAIL <= now), default=None)
        if i is None:
            raise C.Frozen("no N1 cycle yet")
        if (now - self.n1T[i]) / pd.Timedelta(hours=1) > 5:
            raise C.Frozen("N1 stale")
        pos = self.n1_positions(i)
        return float(self.n1L[i]["equity"]), {"N1|" + k: v for k, v in pos.items()}, dict(T=str(self.n1T[i]))

    def f4(self, now):
        ds = [d for d in self.f4o if pd.Timestamp(d) + F4_AVAIL <= now]
        if not ds:
            raise C.Frozen("no F4 output yet")
        d = max(ds)
        eq, comps = C.parse_f4(self.f4o[d])
        return eq, comps, dict(asof=d)

    def filters(self):
        return self.filt

    def coin(self, p):
        return self.coin_of.get(p) or (p[4:] if p.startswith("1000") and not p.startswith("1000000") else p[7:] if p.startswith("1000000") else p)

    def prices(self, perps):
        h = self.now.floor("h")
        out = {}
        for p in perps:
            b = self.sim.bar(p, self.coin(p), h)
            if b is not None:
                out[p] = float(b.open)
        self._px = out
        return out

    def prices_after(self):
        h1 = self.now.floor("h") + pd.Timedelta(hours=1)
        out = dict(self._px)
        for p in set(self._px) | set(self.sim.pos):
            b = self.sim.bar(p, self.coin(p), h1)
            if b is not None:
                out[p] = float(b.open)
        return out

    def highs(self, perps, since, now):
        out = {}
        for p in perps:
            for t in pd.date_range(pd.Timestamp(since).floor("h"), now.floor("h") - pd.Timedelta(hours=1), freq="h"):
                b = self.sim.bar(p, self.coin(p), t)
                if b is not None:
                    out[p] = max(out.get(p, 0.0), float(b.high))
        return out

    def wallet(self):
        return None

    def return_history(self):
        h = pd.read_csv(PROJ / self.cfg["weights"]["history"], parse_dates=["date"]).set_index("date")
        return h.r_1D.dropna(), h.r_N1.dropna()

    def positions(self):
        return dict(self.sim.pos)

    def journal_written(self, st):
        pass

    def execute(self, o, cid):
        px = self.sim.market(o["perp"], self.coin(o["perp"]), o["qty"], self.now.floor("h") + pd.Timedelta(hours=1))
        if px is None:
            self.last_error = "no bar"
            return None
        return o["qty"], px

    def recover(self, j):
        return None

    def stop_status(self, ex):
        return {sid: "NEW" for sid in ex}

    def place_stop(self, spec):
        return "replay"

    def cancel_stop(self, e):
        return True

    def funding(self, held, since, now):
        out = {}
        for p, q in held.items():
            for t, rate, px in self.sim.funding_between(p, self.coin(p), pd.Timestamp(since), pd.Timestamp(now)):
                amt = -q * px * rate
                out[p] = out.get(p, 0.0) + amt
                self.sim.cash += amt
        return out


def run(out_dir, cfg):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    env = ReplayEnv(cfg)
    for coin, v in json.loads((RP / "manifest.json").read_text()).get("f4_names", {}).items():
        if v:
            env.coin_of[v[0]] = coin
    for coin, p in cfg["n1_perp_names"].items():
        env.coin_of[p] = coin
    st = O.new_state()
    lf = out / "ledger.jsonl"
    assert not lf.exists(), "replay ledger exists: use a fresh directory"
    for now in pd.date_range("2026-09-01 00:50", "2026-09-30 22:50", freq="h"):
        env.now = now
        rec = O.cycle(env, st, cfg, now)
        rec["sim_equity"] = env.sim.equity(env.prices_after())
        rec["sim_pos"] = dict(env.sim.pos)
        C.append_ledger(lf, rec)
        if now.hour == 23 or now.hour == 22:
            print(now, round(st["eco_equity"], 2), "sim", round(rec["sim_equity"], 2), "attr", round(rec["acct_pnl"], 2),
                  "orders", len(rec["orders"]), "comps", rec["n_components"], flush=True)
    (out / "state_final.json").write_text(json.dumps(st, indent=1, default=str))
    return st


if __name__ == "__main__":
    cfg = json.loads((PROJ / "deploy" / "eco_config.json").read_text())
    run(sys.argv[1], cfg)
