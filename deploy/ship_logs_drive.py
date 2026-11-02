"""Hourly log shipping to Google Drive + safe freeing. v2 = one verified tar.gz bundle per hour.

Protocol: logs/log_ship/LOG_SHIP_PROTOCOL_PREREGISTERED.md + V2 .. V7 amendments (all SHA-locked).
Nothing is ever deleted on the remote. Local files are freed (F1 idle cron .out chunks, F2 backups/<date> older than 2 days)
ONLY after the hour's bundle MD5 is confirmed on the remote. Hash-chained ledger.
Usage: python ship_logs_drive.py --remote gdrive:CryptoBot_1D_Cloud_VM [--root /opt/cryptobot]
Env RCLONE_CMD (optional, tests): command prefix instead of 'rclone'.
"""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

MIRROR = ["logs/forward_ls_f4", "logs/forward_multi_16b", "logs/strategy_1d_step16_forward", "logs/monitor_n3_evt",
          "logs/collector_m4_options", "logs/cost_study_step2", "logs/futures_testnet_f6", "logs/cron_status",
          "logs/daily_status", "logs/log_ship", "logs/forward_recorder_r2", "data/forward/rest_raw", "data/forward/depth_raw",
          "data/forward/models", "data/forward_f4", "data/collector_m4", "data/forward_r2", "backups", "deploy/crontab.txt",
          # v3 amendment (LOG_SHIP_PROTOCOL_V3_AMENDMENT.md): ECO and PAPER-N1
          "data/eco", "data/eco_demo", "data/eco_shadow", "logs/eco", "data/paper_n1", "data/paper_n1_test_cycle_20261021",
          "logs/paper_n1", "deploy/eco_config.json", "deploy/eco_history_daily_returns.csv", "deploy/paper_n1_config.json",
          "deploy/crontab_backup_before_R2_20261019.txt", "deploy/crontab_backup_before_PAPERN1_20261021.txt",
          "deploy/crontab_backup_before_ECO_20261022.txt",
          # v5 amendment (LOG_SHIP_PROTOCOL_V5_AMENDMENT.md): EMO meter + EMO-1 records (raw zips are not shipped)
          "logs/emotion", "data/emotion/ledger.jsonl", "data/emotion/emo1_raw/manifest.csv", "data/emotion/emo1_raw/eligible.json",
          "data/emotion/emo1_raw/symbols.json", "deploy/crontab_backup_before_A2_20261022.txt",
          # v6 amendment (LOG_SHIP_PROTOCOL_V6_AMENDMENT.md): ECO demo cut-over + PAPER-SPOT-S1
          "data/paper_spot_s1", "logs/paper_spot_s1", "deploy/crontab_backup_before_cutover_20261025.txt"]
SKIP_NAMES = {"RUNNING.lock", "md5_cache.json", "shipped_index.json"}
OUT_IDLE_S, BACKUP_KEEP_DAYS, LOCK_STALE_S = 15 * 60, 2, 2 * 3600
PROC = Path(os.environ.get("LOGSHIP_PROC_ROOT", "/proc"))       # v4: tests point this at a fake process root


def open_by_process(f):
    """v4: True if any process holds f open (/proc/<pid>/fd links). No /proc (laptop) -> False (v2 behaviour)."""
    if not PROC.is_dir():
        return False
    target = str(Path(f).resolve())
    for pid in PROC.iterdir():
        if not pid.name.isdigit():
            continue
        try:
            fds = list((pid / "fd").iterdir())
        except OSError:                                         # process gone / not ours
            continue
        for fd in fds:
            try:
                t = os.readlink(fd) if fd.is_symlink() else fd.read_text().strip()     # a plain file = the test stub
            except OSError:
                continue
            if t == target:
                return True
    return False


def take_lock(lock):
    """v7: atomic create (O_EXCL), so two runs started together cannot both pass. A lock older than LOCK_STALE_S is taken over once."""
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime < LOCK_STALE_S:
                    return False
                lock.unlink()
            except FileNotFoundError:                               # the other run just finished
                pass
            continue
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    return False


def digest(p, algo):
    h = hashlib.new(algo)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Rclone:
    def __init__(self):
        self.cmd = shlex.split(os.environ.get("RCLONE_CMD", "rclone"))
        self.errors = []

    def run(self, *args):
        p = subprocess.run(self.cmd + list(args), capture_output=True, text=True)
        if p.returncode != 0:
            self.errors.append(f"{args[0]} rc={p.returncode} {p.stderr.strip()[:200]}")
            return None
        return p.stdout

    def hashes(self, path):
        out = self.run("lsjson", "-R", "--hash", "--files-only", path)
        return {} if out is None else {e["Path"]: (e.get("Hashes") or {}).get("md5") for e in json.loads(out or "[]")}


def local_files(root, cache):
    out = {}
    for item in MIRROR:
        p = root / item
        files = [p] if p.is_file() else (sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [])
        for f in files:
            if f.name.endswith(".shipping") or f.name in SKIP_NAMES:
                continue
            rel = f.relative_to(root).as_posix()
            st = f.stat()
            key = f"{st.st_size}:{st.st_mtime_ns}"
            if cache.get(rel, {}).get("key") != key:
                cache[rel] = dict(key=key, md5=digest(f, "md5"))
            out[rel] = dict(size=st.st_size, md5=cache[rel]["md5"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", required=True)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args()
    root, remote = Path(a.root), a.remote.rstrip("/")
    led_dir = root / "logs" / "log_ship"
    (led_dir / "manifests").mkdir(parents=True, exist_ok=True)
    lock = led_dir / "RUNNING.lock"
    if not take_lock(lock):
        print("another ship run is active -> exit"); return 0
    try:
        for _ in range(100):                                              # v7: never reuse the (hour, tag) of an earlier run
            now = datetime.now(timezone.utc)
            hour, tag = now.strftime("%Y-%m-%d_%H"), now.strftime("%H%M%S")
            if not any((led_dir / "manifests" / f"{hour}_{tag}{s}").exists() for s in (".json", ".result.json")):
                break
            time.sleep(0.1)
        else:
            print(f"no free run tag after 10 s (last {hour} {tag}) -> exit, nothing written"); return 1
        rc = Rclone()
        cache_p, idx_p = led_dir / "md5_cache.json", led_dir / "shipped_index.json"
        cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
        shipped = json.loads(idx_p.read_text()) if idx_p.exists() else {}
        # F1 step 1: rename idle .out files (new appends go to a fresh .out)
        cs = root / "logs" / "cron_status"
        busy = []
        for f in sorted(cs.glob("*.out")) if cs.exists() else []:
            if f.stat().st_size > 0 and time.time() - f.stat().st_mtime >= OUT_IDLE_S:
                if open_by_process(f):                                    # v4: a running job still writes to it
                    busy.append(f.name)
                    continue
                f.rename(f.with_name(f.name + ".shipping"))
        shipping = sorted(cs.glob("*.out.shipping")) if cs.exists() else []
        loc = local_files(root, cache)
        cache_p.write_text(json.dumps(cache))
        todo = sorted(r for r, v in loc.items() if shipped.get(r) != v["md5"])
        members = [dict(path=r, size=loc[r]["size"], md5=loc[r]["md5"], sha256=digest(root / r, "sha256"), kind="mirror") for r in todo]
        members += [dict(path=f.relative_to(root).as_posix(), size=f.stat().st_size, md5=digest(f, "md5"),
                         sha256=digest(f, "sha256"), kind="rotated_out") for f in shipping]
        verified, bundle_md5, man_md5, bundle_bytes = False, "", "", 0
        rotated, freed, freed_bytes = [], [], 0
        mp = led_dir / "manifests" / f"{hour}_{tag}.json"
        man = dict(hour=hour, run_utc=now.isoformat(), remote=remote, members=members)
        if members:
            with tempfile.TemporaryDirectory() as td:
                bp = Path(td) / f"bundle_{tag}.tar.gz"
                with tarfile.open(bp, "w:gz") as tar:
                    for m in members:
                        tar.add(root / m["path"], arcname=m["path"])
                mp.write_text(json.dumps(man, indent=1))
                bundle_md5, man_md5, bundle_bytes = digest(bp, "md5"), digest(mp, "md5"), bp.stat().st_size
                dst = f"{remote}/hourly/{hour}"
                ok1 = rc.run("copyto", str(bp), f"{dst}/bundle_{tag}.tar.gz") is not None
                ok2 = rc.run("copyto", str(mp), f"{dst}/bundle_{tag}_manifest.json") is not None
                got = rc.hashes(dst) if ok1 and ok2 else {}
                verified = (got.get(f"bundle_{tag}.tar.gz") == bundle_md5 and got.get(f"bundle_{tag}_manifest.json") == man_md5
                            and not rc.errors)
        else:
            mp.write_text(json.dumps(man, indent=1))
        if verified:
            for m in members:
                if m["kind"] == "mirror":
                    shipped[m["path"]] = m["md5"]
            idx_tmp = led_dir / "shipped_index.json.tmp"
            idx_tmp.write_text(json.dumps(shipped))
            os.replace(idx_tmp, idx_p)
            for f in shipping:                                            # F1 step 2
                rotated.append(f.relative_to(root).as_posix()); freed_bytes += f.stat().st_size; f.unlink()
        if verified or (not members and not rc.errors):                   # F2: only from the confirmed index
            cutoff = (now - timedelta(days=BACKUP_KEEP_DAYS)).date()
            for d in sorted(p for p in (root / "backups").glob("*") if p.is_dir()) if (root / "backups").exists() else []:
                try:
                    day = datetime.strptime(d.name, "%Y-%m-%d").date()
                except ValueError:
                    continue
                files = [x for x in d.rglob("*") if x.is_file()]
                if day >= cutoff or not files:
                    continue
                if all(shipped.get(x.relative_to(root).as_posix()) == digest(x, "md5") for x in files):
                    for x in files:
                        freed.append(dict(file=x.relative_to(root).as_posix(), md5=digest(x, "md5"))); freed_bytes += x.stat().st_size
                        x.unlink()
                    for sub in sorted((p for p in d.rglob("*") if p.is_dir()), reverse=True):
                        sub.rmdir()
                    d.rmdir()
        man.update(verified=verified, bundle_md5=bundle_md5, rotated_out=rotated, freed_backups=freed, rclone_errors=rc.errors, out_busy=busy)
        (led_dir / "manifests" / f"{hour}_{tag}.result.json").write_text(json.dumps(man, indent=1))
        led = led_dir / "ledger.csv"
        prev = "GENESIS"
        if led.exists() and led.stat().st_size:
            prev = led.read_text().strip().splitlines()[-1].split(",")[-1]
        line = dict(run_utc=now.isoformat(), hour=hour, tag=tag, n_files_in_bundle=len(members), bundle_bytes=bundle_bytes,
                    bundle_md5=bundle_md5, manifest_md5=man_md5, verified=verified, n_rotated=len(rotated),
                    n_backup_files_freed=len(freed), bytes_freed=freed_bytes, n_rclone_errors=len(rc.errors),
                    manifest_sha256=digest(mp, "sha256"), prev_sha256=prev)
        body = ",".join(str(v) for v in line.values())
        line["line_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        first = not led.exists() or led.stat().st_size == 0
        with open(led, "a") as f:
            if first:
                f.write(",".join(line) + "\n")
            f.write(",".join(str(v) for v in line.values()) + "\n")
        print(f"ship {hour} {tag}: bundle {len(members)} files {bundle_bytes} B, verified {verified}, rotated {len(rotated)}, "
              f"backup files freed {len(freed)}, bytes freed {freed_bytes}, rclone errors {len(rc.errors)} {rc.errors[:2]}")
        return 0 if (verified or not members) and not rc.errors else 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
