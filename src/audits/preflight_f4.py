"""Pre-flight test of the F4 forward path (main) in a SANDBOX (2026-10-16, before the first scheduled run).
Nothing is written to logs/forward_ls_f4 or logs/forward_multi_16b: every path is redirected to a temp folder.
Day 1 = 2026-10-13 (PAPER_START in the sandbox), day 2 = 2026-10-14, with the live data folders.
Signals: the 16B --test prediction files of 2026-10-14; for 2026-10-13 the same files with the dates shifted one day
back (TECHNICAL test data, not a forecast). The 16B paper equity needed for C1 is made with 16B's own paper_from_rows.
Checks: both days run without error, ledger chain of 2 lines, C1 True on day 2, orders file present."""
import sys, json, shutil, tempfile
from pathlib import Path
import pandas as pd
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import forward_ls_f4 as Q
import forward_multi_16b as FB
import forward_dryrun_1d as FD
import core_rows_1d as CR

T = Path(tempfile.mkdtemp(prefix="f4_preflight_"))
src16 = FB.LOG / "test" / "predictions"
(T / "16b" / "predictions").mkdir(parents=True)
(T / "16b" / "paper").mkdir(parents=True)
(T / "f4").mkdir(parents=True)
shutil.copy(Q.LOG / "F4_PROTOCOL_SHA256.txt", T / "f4")
d2 = pd.Timestamp("2026-10-14")
for kind, col in (("d1", "date"), ("h4_r6", "bar"), ("h1_r24", "bar")):
    x = pd.read_csv(src16 / f"{kind}_{d2.date()}.csv", parse_dates=[col])
    x.to_csv(T / "16b" / "predictions" / f"{kind}_{d2.date()}.csv", index=False)
    x.assign(**{col: x[col] - pd.Timedelta(days=1)}).to_csv(T / "16b" / "predictions" / f"{kind}_{(d2 - pd.Timedelta(days=1)).date()}.csv", index=False)
FB.PRED, FB.PAPER, FB.LEDGER = T / "16b" / "predictions", T / "16b" / "paper", T / "16b" / "ledger.csv"
FB.PAPER_START = Q.PAPER_START = pd.Timestamp("2026-10-13")
Q.LOG, Q.LEDGER, Q.RUNLOG, Q.PERP_DIR = T / "f4", T / "f4" / "ledger.csv", T / "f4" / "run_log.txt", T / "perp"
rows = []
for day in (pd.Timestamp("2026-10-13"), d2):
    line = dict(asof=str(day.date()), test=False, line_sha256=f"sandbox-{day.date()}",
                d1_sha256=FD.sha_file(FB.PRED / f"d1_{day.date()}.csv"), h4_sha256=FD.sha_file(FB.PRED / f"h4_r6_{day.date()}.csv"),
                h1_sha256=FD.sha_file(FB.PRED / f"h1_r24_{day.date()}.csv"))
    rows.append(line)
    pd.DataFrame(rows).to_csv(FB.LEDGER, index=False)
    if day == FB.PAPER_START:
        eq = pd.DataFrame(dict(date=[day], D1=[10000.0], H4=[10000.0], H1=[10000.0], M_AI3=[10000.0]))
    else:
        dk, lk, dn, ln, _ = CR.load_folder(FD.LIVE1D, FD.LIVE1H, day)
        d1, _ = FB.load_scores("d1", day, FB.PRED); h4, _ = FB.load_scores("h4_r6", day, FB.PRED); h1, _ = FB.load_scores("h1_r24", day, FB.PRED)
        eq, _ = FB.paper_from_rows(FB.PAPER_START, day, d1, h4, h1, {**dk, **dn}, {**lk, **ln}, FD.LIVE1H)
    eq.to_csv(FB.PAPER / f"equity_{day.date()}.csv", index=False)
    Q.main(asof=day)
L = pd.read_csv(Q.LEDGER)
assert len(L) == 2 and L.prev_sha256.iloc[0] == "GENESIS" and L.prev_sha256.iloc[1] == L.line_sha256.iloc[0], L
assert bool(L.C1.iloc[1]), L.notes.iloc[1]
assert (Q.LOG / "paper" / "orders_2026-10-14.json").exists()
o = json.loads((Q.LOG / "paper" / "orders_2026-10-14.json").read_text())
print(L[["asof", "C1", "LS_RS", "LS_F2", "LO", "n_perp", "n_shortable_today", "on_time"]].to_string())
print("orders LS_RS:", {k: dict(short=v["short"], cover=v["cover"]) for k, v in o.get("LS_RS", {}).items()})
print(f"[PREFLIGHT F4 PASS] two sandbox days ran; chain OK; C1 True; orders file written (sandbox {T})")
