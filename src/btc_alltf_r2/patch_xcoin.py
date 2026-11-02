"""BTC-ALLTF-R2 amendment 1 (2026-10-29, after the lock; R2_CODE_CHANGES_AFTER_LOCK.md entry 4): exact patch of a finished cross-coin job
for the coins whose data has a relisting break (see xcoin.refine_segments). Accumulators are sums over coins, so
    corrected = full run - (those coins, locked code) + (those coins, amendment 1)
The "locked code" part must reproduce the coins' rows of the full run exactly (checked here; any difference stops the patch).
Unaffected jobs are copied unchanged. Output: <RUN>/xcoin_v2/<job>/ (acc.npz, per_coin.parquet, coins.csv, PATCH.json, DONE.json).
Usage: python src/btc_alltf_r2/patch_xcoin.py --run <R2 RUN dir> --job spot_1h_S2"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402
import xcoin as XC                                                            # noqa: E402


def affected(market, tf, coins):
    out = []
    for c in coins:
        close, _ = K.daily(c, market, XC.LO, XC.HI)
        s0 = XC.segments(market, tf, c)
        if XC.refine_segments(s0, close) != s0:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--job", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    market, tf, fam = a.job.split("_")
    src = run / "xcoin" / a.job
    dst = run / "xcoin_v2" / a.job
    if (dst / "DONE.json").exists():
        print("patched already"); return
    if not (src / "DONE.json").exists():
        raise SystemExit("source job not finished")
    coins = pd.read_csv(src / "coins.csv").coin.tolist()
    aff = affected(market, tf, coins)
    dst.mkdir(parents=True, exist_ok=True)
    info = dict(job=a.job, affected=aff)
    if not aff:
        for f in ("acc.npz", "per_coin.parquet", "coins.csv"):
            shutil.copy(src / f, dst / f)
        info["note"] = "no coin of this job is changed by amendment 1: copied unchanged"
    else:
        for tag, fix in (("patch_old", False), ("patch_new", True)):
            if not (run / tag / a.job / "DONE.json").exists():
                cmd = [sys.executable, str(Path(__file__).resolve().parent / "xcoin.py"), "--run", str(run), "--market", market, "--tf", tf,
                       "--family", fam, "--coins", ",".join(aff), "--xdir", tag] + (["--fix"] if fix else [])
                subprocess.run(cmd, check=True, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}, stdout=subprocess.DEVNULL)
        F = np.load(src / "acc.npz", allow_pickle=False)
        O = np.load(run / "patch_old" / a.job / "acc.npz", allow_pickle=False)
        N = np.load(run / "patch_new" / a.job / "acc.npz", allow_pickle=False)
        pf, po, pn = (pd.read_parquet(d / "per_coin.parquet") for d in (src, run / "patch_old" / a.job, run / "patch_new" / a.job))
        cols = ["k", "coin", "n", "wins", "sum_net", "equity", "equity_2xfee", "expo", "den_days", "sharpe", "bh", "first_in", "last_out"]
        A = pf[pf.coin.isin(aff)][cols].sort_values(["coin", "k"]).reset_index(drop=True)
        B = po[cols].sort_values(["coin", "k"]).reset_index(drop=True) if len(po) else po
        same = len(A) == len(B) and all(np.allclose(A[c].astype(float), B[c].astype(float), equal_nan=True, rtol=0, atol=0) if c != "coin"
                                        else (A[c] == B[c]).all() for c in cols)
        if not same:
            raise SystemExit("locked-code re-run of the affected coins does NOT reproduce the full run: patch refused")
        if not (np.array_equal(O["BHS"], N["BHS"]) and np.array_equal(O["BHD"], N["BHD"])):
            raise SystemExit("benchmark changed by the fix: not expected")
        out = {k: F[k] for k in F.files}
        for k in ("SR", "SR2", "SEX"):
            out[k] = F[k] - O[k] + N[k]
        out["DEN"] = (F["DEN"].astype(np.int64) - O["DEN"] + N["DEN"]).astype(np.int32)
        np.savez(dst / "acc.npz", **out)
        pd.concat([pf[~pf.coin.isin(aff)], pn], ignore_index=True).sort_values(["k", "coin"]).to_parquet(dst / "per_coin.parquet", index=False)
        cf, cn = pd.read_csv(src / "coins.csv"), pd.read_csv(run / "patch_new" / a.job / "coins.csv")
        pd.concat([cf[~cf.coin.isin(aff)], cn], ignore_index=True).sort_values("coin").to_csv(dst / "coins.csv", index=False)
        info.update(reproduced_locked_rows=int(len(A)), max_abs_change_SR=float(np.abs(out["SR"] - F["SR"]).max()),
                    den_change=int(np.abs(out["DEN"].astype(np.int64) - F["DEN"]).sum()))
    (dst / "PATCH.json").write_text(json.dumps(info, indent=1))
    files = sorted(p for p in dst.iterdir() if p.is_file() and p.name != "DONE.json")
    (dst / "DONE.json").write_text(json.dumps({p.name: K.sha(p) for p in files} | {"finished_utc": pd.Timestamp.now("UTC").isoformat(),
                                                                                  "fee_per_side": json.loads((src / "DONE.json").read_text())["fee_per_side"]}, indent=1))
    print(f"PATCHED {a.job}: affected {aff}")


if __name__ == "__main__":
    main()
