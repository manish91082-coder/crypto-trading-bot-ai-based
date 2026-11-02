"""Verifier for logs/r2_4h_a0/trial_registry.csv (A0 §8-§9): chain, line hashes, config hashes, linked SHAs, budget.
R1 hash chain + line hashes      R2 config_sha256 == sha256 of the stored config (';' was written for ',')
R3 a0 / sub-protocol / data SHAs == the locked files      R4 every RESULT line points to the current result files
R5 distinct trials registered <= 20 (budget) and every registered trial has exactly one RESULT line or is PENDING"""
import hashlib
import sys
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
reg = Path(sys.argv[1]) if len(sys.argv) > 1 else R_ / "logs" / "r2_4h_a0" / "trial_registry.csv"   # arg: tamper tests on a copy
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


lines = reg.read_text().strip().splitlines()
head, rows = lines[0].split(","), [l.split(",") for l in lines[1:]]
prev, c1, c2 = "GENESIS", True, True
for r in rows:
    d = dict(zip(head, r))
    c1 &= len(r) == len(head) and d["prev_sha256"] == prev and hashlib.sha256(",".join(r[:-1]).encode()).hexdigest() == d["line_sha256"]
    if d["config"].startswith("b64:"):                                   # REG-NOTE lines: exact config, base64
        import base64
        c2 &= hashlib.sha256(base64.b64decode(d["config"][4:])).hexdigest() == d["config_sha256"]
    elif hashlib.sha256(d["config"].replace(";", ",").encode()).hexdigest() != d["config_sha256"]:
        # lossy ';' encoding (config itself contained ';'): valid only if a REG-NOTE line carries the exact config with that hash
        notes = [l.split(",") for l in lines[1:] if l.split(",")[2] == "REG-NOTE" and l.split(",")[0] == d["trial_id"]]
        c2 &= any(n[4] == d["config_sha256"] for n in notes)
    prev = d["line_sha256"]
ok("R1", c1, f"{len(rows)} registry lines: hash chain and line hashes intact")
ok("R2", c2, "every config_sha256 equals the sha256 of its stored config")
a0 = R_ / "logs" / "r2_4h_a0" / "A0_4H_PROTOCOL_PREREGISTERED.md"
a1 = R_ / "logs" / "r2_4h_a1" / "A1_PROTOCOL_PREREGISTERED.md"
locks = {"A1": (sha(a1), (a1.parent / "A1_PROTOCOL_SHA256.txt").read_text().split()[0])}
a0s, a0l = sha(a0), (a0.parent / "A0_PROTOCOL_SHA256.txt").read_text().split()[0]
legs = sha(R_ / "data" / "derived" / "swing_anatomy" / "legs_all.parquet")
c3 = a0s == a0l
for r in rows:
    d = dict(zip(head, r))
    if d["step"] == "A1":
        c3 &= d["a0_sha256"] == a0s and d["sub_protocol_sha256"] == locks["A1"][0] == locks["A1"][1] and d["data_sha256"] == legs
ok("R3", c3, "A0 / A1 protocol SHAs == locks; data SHA == legs_all.parquet")
gate, trades = sha(R_ / "logs" / "r2_4h_a1" / "A1_gate.csv"), sha(R_ / "logs" / "r2_4h_a1" / "a1_trades.parquet")
c4 = all(dict(zip(head, r))["result_sha256"] == gate and dict(zip(head, r))["data_sha256"] == trades
         for r in rows if dict(zip(head, r))["step"] == "A1-RESULT")
cg, ct = sha(R_ / "logs" / "r2_4h_a1" / "correction" / "A1c_gate.csv"), sha(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")
am2 = R_ / "logs" / "r2_4h_a0" / "A0_AMENDMENT_2.md"
c4c = all(dict(zip(head, r))["result_sha256"] == cg and dict(zip(head, r))["data_sha256"] == ct
          and dict(zip(head, r))["sub_protocol_sha256"] == sha(am2) == (am2.parent / "A0_AMENDMENT_2_SHA256.txt").read_text().split()[0]
          for r in rows if dict(zip(head, r))["step"] == "A1-CORRECTION-RESULT")
t14c = R_ / "logs" / "r2_4h_t14" / "claims_t14.json"
c4t = all(dict(zip(head, r))["result_sha256"] == sha(t14c) and dict(zip(head, r))["sub_protocol_sha256"] == sha(t14c.parent / "T14_PROTOCOL_PREREGISTERED.md")
          for r in rows if dict(zip(head, r))["step"] == "T14-RESULT")
NRES = {"N1-RESULT": ("research_n1_portfolio", "claims_n1.json", "N1_PROTOCOL_PREREGISTERED.md"),
        "N2-RESULT": ("research_n2_regime", "claims_n2.json", "N2_PROTOCOL_PREREGISTERED.md"),
        "N3-RESULT": ("research_n3_execution", "claims_n3.json", "N3_PROTOCOL_PREREGISTERED.md"),
        "N5-RESULT": ("research_n5_ai", "claims_n5.json", "N5_PROTOCOL_PREREGISTERED.md"),
        "N6S-RESULT": ("research_n6_safety_sizing", "claims_n6.json", "N6_PROTOCOL_PREREGISTERED.md"),
        "N6A-RESULT": ("research_n6_safety_sizing", "claims_n6.json", "N6_PROTOCOL_PREREGISTERED.md")}
c4n = all(dict(zip(head, r))["result_sha256"] == sha(R_ / "logs" / NRES[dict(zip(head, r))["step"]][0] / NRES[dict(zip(head, r))["step"]][1])
          and dict(zip(head, r))["sub_protocol_sha256"] == sha(R_ / "logs" / NRES[dict(zip(head, r))["step"]][0] / NRES[dict(zip(head, r))["step"]][2])
          for r in rows if dict(zip(head, r))["step"] in NRES)
c4 = c4 and c4n
ok("R4", c4 and c4c and c4t, "every A1-RESULT line points to the original A1 files; every A1-CORRECTION-RESULT line to the correction files + locked amendment 2; T14-RESULT to claims_t14.json + T14 protocol; N*-RESULT to their claims + protocols")
reg_ids = [dict(zip(head, r))["trial_id"] for r in rows if not dict(zip(head, r))["step"].endswith("RESULT") and dict(zip(head, r))["step"] != "REG-NOTE"]
res_ids = [dict(zip(head, r))["trial_id"] for r in rows if dict(zip(head, r))["step"] in ("A1-RESULT", "A3-RESULT", "A4-RESULT", "T14-RESULT", "N1-RESULT", "N2-RESULT", "N3-RESULT", "N5-RESULT", "N6S-RESULT", "N6A-RESULT")]   # corrections are extra lines, not new trials
c5 = len(set(reg_ids)) == len(reg_ids) <= 20 and all(res_ids.count(t) <= 1 for t in reg_ids) and set(res_ids) <= set(reg_ids)
ok("R5", c5, f"trials registered {len(reg_ids)} of 20, with result {len(set(res_ids))}, pending {len(set(reg_ids) - set(res_ids))}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
