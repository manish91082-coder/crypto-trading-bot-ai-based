"""Live collector of Binance USD-M futures liquidation orders (public stream !forceOrder@arr, all symbols). Public data only, no keys,
no orders. Binance publishes no liquidation history, so this builds our own (logs/live_collect/LIQ_COLLECTOR_RECORD.md).
Stdlib-only websocket client (RFC 6455: handshake, masked client frames, ping -> pong, close), so no package is installed.
Writes data/live_collect/liq/YYYY-MM-DD.jsonl (UTC day of receipt, one raw message per line + receive time), a session log with every
connect / disconnect (so gaps are explicit), and on day change gzips the finished day and records its SHA256 in MANIFEST.csv.
Singleton via flock (cron starts it every 5 min; a second copy exits at once). Usage: python src/collect/liq_collector.py [--seconds N]"""
import argparse
import base64
import fcntl
import gzip
import hashlib
import json
import os
import shutil
import socket
import ssl
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
ROOT = PROJ / "data/live_collect/liq"
HOST, PATH = "fstream.binance.com", "/market/ws/!forceOrder@arr"   # checked 2026-10-26: the old /ws/ path upgrades but sends no data


def now():
    return datetime.now(timezone.utc)


def slog(msg):
    with open(ROOT / "sessions.log", "a", encoding="utf-8") as f:
        f.write(f"{now():%Y-%m-%dT%H:%M:%S.%fZ} {msg}\n")


def connect():
    raw = socket.create_connection((HOST, 443), timeout=30)
    s = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
    hdr = b""
    while b"\r\n\r\n" not in hdr:
        ch = s.recv(1)
        if not ch:
            raise ConnectionError("closed during handshake")
        hdr += ch
    if b" 101 " not in hdr.split(b"\r\n", 1)[0]:
        raise ConnectionError(hdr.split(b"\r\n", 1)[0].decode(errors="replace"))
    acc = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
    if acc.encode() not in hdr:
        raise ConnectionError("bad Sec-WebSocket-Accept")
    s.settimeout(240)                                       # Binance pings every ~3 min; no frame for 4 min = dead link
    return s


def recv_exact(s, n):
    b = b""
    while len(b) < n:
        ch = s.recv(n - len(b))
        if not ch:
            raise ConnectionError("socket closed")
        b += ch
    return b


def send_frame(s, opcode, payload=b""):
    mask = os.urandom(4)
    n = len(payload)
    head = bytes([0x80 | opcode])
    head += bytes([0x80 | n]) if n < 126 else (bytes([0x80 | 126]) + struct.pack(">H", n))
    s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def frames(s):
    buf, op0 = b"", None
    while True:
        b1, b2 = recv_exact(s, 2)
        fin, op = b1 & 0x80, b1 & 0x0F
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", recv_exact(s, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", recv_exact(s, 8))[0]
        mk = recv_exact(s, 4) if b2 & 0x80 else None
        data = recv_exact(s, n)
        if mk:
            data = bytes(c ^ mk[i % 4] for i, c in enumerate(data))
        if op == 0x9:
            send_frame(s, 0xA, data)
            continue
        if op == 0xA:
            continue
        if op == 0x8:
            raise ConnectionError(f"server close {data[:2].hex()}")
        if op in (0x1, 0x2):
            buf, op0 = data, op
        elif op == 0x0:
            buf += data
        if fin and op0 is not None:
            yield buf.decode()
            buf, op0 = b"", None


def close_day(day):
    src = ROOT / f"{day}.jsonl"
    if not src.exists():
        return
    dst = ROOT / f"{day}.jsonl.gz"
    with open(src, "rb") as fi, gzip.open(dst, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    n = sum(1 for _ in gzip.open(dst, "rt", encoding="utf-8"))
    with open(ROOT / "MANIFEST.csv", "a", encoding="utf-8") as f:
        if f.tell() == 0:
            f.write("day,file,lines,sha256,closed_utc\n")
        f.write(f"{day},{dst.name},{n},{hashlib.sha256(dst.read_bytes()).hexdigest()},{now():%Y-%m-%dT%H:%M:%SZ}\n")
    src.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0, help="stop after N seconds (test); 0 = run until killed")
    a = ap.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    lockf = open(ROOT / ".lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0                                             # another copy is running
    t_end = time.time() + a.seconds if a.seconds else None
    for f in ROOT.glob("*.jsonl"):                            # days left open by a previous run
        if f.stem < f"{now():%Y-%m-%d}":
            close_day(f.stem)
    backoff = 1
    while t_end is None or time.time() < t_end:
        try:
            s = connect()
            slog("CONNECT")
            backoff = 1
            day = f"{now():%Y-%m-%d}"
            out = open(ROOT / f"{day}.jsonl", "a", encoding="utf-8")
            for msg in frames(s):
                t = now()
                d = f"{t:%Y-%m-%d}"
                if d != day:
                    out.close(); close_day(day); day = d
                    out = open(ROOT / f"{day}.jsonl", "a", encoding="utf-8")
                out.write(json.dumps({"rx": t.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "m": json.loads(msg)}, separators=(",", ":")) + "\n")
                out.flush()
                with open(ROOT / "heartbeat.txt", "w") as hb:
                    hb.write(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
                if t_end is not None and time.time() >= t_end:
                    break
            out.close()
            s.close()
            slog("STOP (test duration reached)" if t_end is not None else "DISCONNECT (stream ended)")
        except Exception as e:                                 # noqa: BLE001  (log + reconnect; the gap is recorded)
            slog(f"DISCONNECT {type(e).__name__}: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
