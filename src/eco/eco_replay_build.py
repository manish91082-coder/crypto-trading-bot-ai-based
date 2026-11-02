"""E-3 inputs (protocol §6), laptop only. Builds the producer outputs of 2026-09 with the DEPLOYED producer code:
  F4: forward_ls_f4.build_lines (as its --test: stored research predictions, archive perp files), run once per as-of day
      2026-09-01..2026-09-30 -> the LS_RS orders dict of that day (exactly the F4 main() expression).
  N1: paper_n1_portfolio.py --replay 2026-08-01 2026-10-01 into data/derived/eco/replay/n1 (August = warm-up).
Writes data/derived/eco/replay/{f4_orders.json, f4_stops.csv, manifest.json}."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
for p in ("src", "src/pipeline_1d", "src/analytics", "src/execution", "src/research"):
    sys.path.insert(0, str(PROJ / p))
OUT = PROJ / "data" / "derived" / "eco" / "replay"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_f4():
    import forward_ls_f4 as F4
    start, end = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
    I = F4.F7R.load("MAIN")
    rows_all = {k: r[(r.t >= start) & (r.t <= end + pd.Timedelta(hours=23))].reset_index(drop=True) for k, r in I["rows"]["AI"].items()}
    del I
    dk, lk, dn, ln_, _ = F4.CR.load_folder(F4.F2R.S13.UNI / "1d", F4.F2R.S13.UNI / "1h", end)
    data, last = {**dk, **dn}, {**lk, **ln_}
    syms = sorted(set().union(*[set(r.symbol) for r in rows_all.values()]))
    names = F4.perp_names(syms)
    ph, fu = F4.arch(names)
    spot1h = {s: F4.S24.bars_1h(F4.F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in syms
              if (F4.F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").exists()}
    gate = F4.gate_table(ph, spot1h, list(pd.date_range(start, end, freq="D")))
    orders, stops = {}, None
    for asof in pd.date_range(start, end, freq="D"):
        rows = {k: r[r.t <= asof + pd.Timedelta(hours=23)].reset_index(drop=True) for k, r in rows_all.items()}
        lines, detail = F4.build_lines(start, asof, rows, data, last, F4.F2R.S24.UNI1H, ph, fu, gate)
        orders[str(asof.date())] = {k: dict(r["pending"], equity_close=float(lines["LS_RS"][k].iloc[-1]))
                                    for k, r in detail["LS_RS"].items()}
        if asof == end:
            stops = pd.concat([r["trades"].assign(sleeve=k) for k, r in detail["LS_RS"].items() if len(r["trades"])], ignore_index=True)
        print("F4", asof.date(), {k: round(v["equity_close"], 2) for k, v in orders[str(asof.date())].items()}, flush=True)
    (OUT / "f4_orders.json").write_text(json.dumps(orders, indent=1, default=str))
    stops[stops.reason == "stop"].to_csv(OUT / "f4_stops.csv", index=False)
    return dict(names={s: v for s, v in names.items()})


def build_n1():
    root = OUT / "n1"
    if (root / "ledger.jsonl").exists():
        raise SystemExit("n1 replay root exists: delete it first (no silent overwrite)")
    r = subprocess.run([sys.executable, str(PROJ / "src" / "execution" / "paper_n1_portfolio.py"), "--root", str(root),
                        "--replay", "2026-08-01", "2026-10-01"], capture_output=True, text=True)
    (OUT / "n1_replay_stdout.txt").write_text(r.stdout + r.stderr)
    assert r.returncode == 0, r.stderr[-2000:]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1:] or ["f4", "n1"]
    info = {}
    if "n1" in what:
        build_n1()
    if "f4" in what:
        info = build_f4()
    man = dict(files={p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()},
               code={n: sha(PROJ / n) for n in ("src/execution/forward_ls_f4.py", "src/execution/paper_n1_portfolio.py", "src/eco/eco_replay_build.py")},
               f4_names=info.get("names"))
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1, default=str))
    print("manifest", len(man["files"]), "files")
