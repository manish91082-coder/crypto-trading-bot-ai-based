"""Independent verifier for ATLAS-TF-2026-10-28 (protocol logs/tf_atlas_2026_10_28/ATLAS_PROTOCOL_PREREGISTERED.md).

Own resolver, own tier and rank logic; does NOT import src/research/tf_atlas.py. Exits 1 on any FAIL.
V1 source SHAs | V2 every raw value re-read from its locator + derived fields recomputed | V3 tiers | V4 ranks
V5 chance table | V6 report claims (if claims.json exists) | V7 coverage of included studies | V8 protocol SHA
"""
import csv, hashlib, json, math, re, sys
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
D = PROJ / "logs/tf_atlas_2026_10_28"
FEE = 0.00092
res = []


def check(name, ok, msg):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {msg}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- own resolver
_cache = {}


def table(f, txt=False):
    k = (f, txt)
    if k not in _cache:
        if txt:
            lines = (PROJ / f).read_text(encoding="utf-8").splitlines()
            i = [j for j, l in enumerate(lines) if l.split()[:2] == ["tf", "direction"]][0]
            hdr = lines[i].split()
            _cache[k] = [dict(zip(hdr, l.split())) for l in lines[i + 1:] if len(l.split()) == len(hdr)]
        else:
            with open(PROJ / f, newline="", encoding="utf-8") as fh:
                _cache[k] = list(csv.DictReader(fh))
    return _cache[k]


def jload(f):
    if f not in _cache:
        _cache[f] = json.loads((PROJ / f).read_text(encoding="utf-8"))
    return _cache[f]


def conv(o, scale):
    if isinstance(o, bool):
        return o
    if isinstance(o, str):
        if o in ("True", "False", "true", "false"):
            return o.lower() == "true"
        if o == "":
            return None
        try:
            o = float(o)
        except ValueError:
            return o
    if isinstance(o, (int, float)) and scale != 1.0:
        return float(o) * scale
    return o


def get(loc):
    if "const" in loc:
        return loc["const"]
    if "calc" in loc:
        a = [get(x) for x in loc["args"]]
        if any(v is None for v in a):
            return None
        a = [float(v) for v in a]
        k = loc.get("k")
        op = loc["calc"]
        if op == "sub":
            return a[0] - a[1]
        if op == "lin":
            return a[0] + k * a[1]
        if op == "add":
            return a[0] + k
        if op == "flip":
            return a[0] if a[0] >= 0.5 else 1 - a[0]
        if op == "efflo":
            return a[1] if a[0] >= 0.5 else 1 - a[2]
        raise ValueError(op)
    if "path" in loc:
        o = jload(loc["f"])
        for p in loc["path"]:
            o = o[p]
        return conv(o, loc.get("scale", 1.0))
    rows = table(loc["f"], txt="txt" in loc)
    key = loc.get("txt") or loc["key"]
    hit = [r for r in rows if all(r[k] == str(v) for k, v in key.items())]
    if len(hit) != 1:
        raise ValueError(f"{len(hit)} rows for {loc}")
    return conv(hit[0][loc["col"]], loc.get("scale", 1.0))


def same(a, b, tol=1e-9):
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        na = a is None or (isinstance(a, float) and math.isnan(a))
        nb = b is None or (isinstance(b, float) and math.isnan(b))
        return na and nb
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str):
        return str(a).lower() == str(b).lower()
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))


def rule(r, vals):
    if not r:
        return None
    v = vals.get(r["field"])
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    op, t = r["op"], r.get("thr")
    return {">": lambda: v > t, "<": lambda: v < t, "==": lambda: v == t, "in": lambda: v in t,
            "startswith": lambda: str(v).startswith(t), "true": lambda: v is True}[op]()


def fnum(x):
    if x is None or isinstance(x, (bool, str)):
        return None
    x = float(x)
    return None if math.isnan(x) else x


def my_tier(role, net, ci_lo, mblo, net_sel, ctrl, skill, verdict, xs):
    oos_pos = net is not None and net > 0 and role == "OOS"
    if verdict is True and oos_pos and ci_lo is not None and ci_lo > 0 and ctrl is True and all(x > 0 for x in xs):
        return "E1"
    if oos_pos or (role == "UNFIT" and net is not None and net > 0 and mblo is not None and mblo > 0):
        return "E2"
    if skill is True or ctrl is True:
        return "E3"
    if (net_sel is not None and net_sel > 0) or (role in ("SEL", "UNFIT") and net is not None and net > 0):
        return "E4"
    return "E5"


# ---------------------------------------------------------------- V8 protocol
lines = (D / "PROTOCOL_SHA256.txt").read_text().split("\n")
pok = sha(D / "ATLAS_PROTOCOL_PREREGISTERED.md") == lines[0].split()[0] and sha(D / "study_inventory.csv") == lines[1].split()[0]
check("V8 protocol + inventory SHA", pok, lines[2] if len(lines) > 2 else "")

# ---------------------------------------------------------------- V1 sources
src = list(csv.DictReader(open(D / "atlas_sources.csv", encoding="utf-8")))
bad = [r["path"] for r in src if sha(PROJ / r["path"]) != r["sha256"]]
check("V1 source SHAs", not bad, f"{len(src)} files, mismatches {bad[:5]}")

# ---------------------------------------------------------------- V2 / V3 rows
rows = pd.read_csv(D / "atlas_rows.csv", keep_default_na=True)
b_raw, b_der, b_tier = [], [], []
for _, r in rows.iterrows():
    locs = json.loads(r["loc"])
    raw = json.loads(r["raw"])
    vals = {}
    for k, loc in locs.items():
        try:
            v = get(loc)
        except Exception as e:
            b_raw.append((r.row_id, k, str(e)[:60]))
            continue
        vals[k] = v
        if not same(v, raw.get(k)):
            b_raw.append((r.row_id, k, v, raw.get(k)))
    net, cost, gross = fnum(vals.get("net")), fnum(vals.get("cost")), fnum(vals.get("gross"))
    if gross is None and net is not None and cost is not None:
        gross = net + cost
    fcr = gross / cost if (gross is not None and cost) else None
    fcr092 = gross / FEE if (gross is not None and r["unit"] == "frac") else None
    hit, ps = fnum(vals.get("hit")), fnum(vals.get("p_star"))
    acc = (hit - 0.5) / (ps - 0.5) if (hit is not None and ps is not None and str(r["acc_sym"]) == "True" and ps != 0.5) else None
    extra = [(k, fnum(vals.get(k))) for k in ("ci_lo", "n", "net_sel", "mblo", "auc", "auc_lo", "calmar", "cagr", "maxdd", "dcagr", "gmed")]
    for nm, mine in [("gross", gross), ("net", net), ("cost", cost), ("FCR", fcr), ("FCR092", fcr092), ("ACC_COVER", acc), ("hit", hit), ("p_star", ps)] + extra:
        theirs = r[nm] if nm in r else None
        theirs = None if (theirs is None or (isinstance(theirs, float) and math.isnan(theirs))) else theirs
        if not same(mine, theirs, 1e-7):
            b_der.append((r.row_id, nm, mine, theirs))
    rl = json.loads(r["rules"])
    ctrl, skill, verd = rule(rl["ctrl"], vals), rule(rl["skill"], vals), rule(rl["verdict"], vals)
    xs = [fnum(vals.get(k)) for k in ("x1", "x2", "x3")]
    xs = [x for x in xs if x is not None]
    t = my_tier(r["role"], net, fnum(vals.get("ci_lo")), fnum(vals.get("mblo")), fnum(vals.get("net_sel")), ctrl, skill, verd, xs)
    if t != r["tier"]:
        b_tier.append((r.row_id, t, r["tier"]))
check("V2a raw values re-read from locators", not b_raw, f"{len(rows)} rows, mismatches {len(b_raw)} {b_raw[:3]}")
check("V2b derived gross/FCR/FCR092/ACC_COVER", not b_der, f"mismatches {len(b_der)} {b_der[:3]}")
check("V3 tiers recomputed", not b_tier, f"mismatches {len(b_tier)} {b_tier[:3]}; tiers {rows.tier.value_counts().to_dict()}")

# ---------------------------------------------------------------- V4 ranks
rk = pd.read_csv(D / "atlas_ranked.csv")
order = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5}


def myscore(r):
    if r["mtype"] in ("TRADE", "AGG"):
        return r["FCR092"] if (r["unit"] == "frac" and not pd.isna(r["FCR092"])) else r["FCR"]
    if r["mtype"] == "SKILL":
        return r["auc_lo"]
    if r["mtype"] == "ACC":
        if not pd.isna(r["ACC_COVER"]):
            return r["ACC_COVER"]
        return r["hit"] - r["p_star"] if not (pd.isna(r["hit"]) or pd.isna(r["p_star"])) else None
    if r["mtype"] == "PORT":
        return r["calmar"]
    return None


bad_rank = 0
for (tf, comp, mt), g in rk.groupby(["tf", "component", "mtype"]):
    items = []
    for _, r in g.iterrows():
        sc = myscore(r)
        sc = None if sc is None or (isinstance(sc, float) and math.isnan(sc)) else sc
        items.append((order[r["tier"]], 0 if sc is not None else 1, -(sc or 0), -(0 if pd.isna(r["n"]) else r["n"]), r["row_id"], r["rank"]))
    items.sort(key=lambda z: z[:4])
    for i, it in enumerate(items, 1):
        prev = items[i - 2] if i > 1 else None
        if it[5] != i and not (prev and prev[:4] == it[:4]):
            bad_rank += 1
check("V4 ranks recomputed (ties allowed in any order)", bad_rank == 0, f"{len(rk)} rows, misplaced {bad_rank}")

# ---------------------------------------------------------------- V5 chance
ch = pd.read_csv(D / "atlas_chance.csv")
bad_ch = []
g = rows[(rows.mtype == "TRADE") & (rows.role == "OOS") & rows.net.notna()]
for _, c in ch.iterrows():
    x = g[(g.study == c.study) & (g.tf == c.tf)]
    ok = len(x) == c.configs and same(float((x.net > 0).mean()), c.share_oos_net_pos, 1e-12)
    if x.gross.notna().any():
        ok &= same(float((x.gross.dropna() > 0).mean()), c.share_oos_gross_pos, 1e-12)
    if x.FCR092.notna().any():
        ok &= same(float(x.FCR092.max()), c.best_FCR092, 1e-9)
    if not ok:
        bad_ch.append((c.study, c.tf))
check("V5 chance table recomputed", not bad_ch, f"{len(ch)} grids, mismatches {bad_ch}")

# ---------------------------------------------------------------- V7 coverage
inv = list(csv.DictReader(open(D / "study_inventory.csv", encoding="utf-8")))
inc = {r["folder"] for r in inv if r["include"] == "yes"}
phys = pd.read_csv(D / "atlas_phys.csv")
covered = set(rows.study) | set(phys.study)
check("V7 coverage of included studies", inc <= covered and set(rows.study) <= inc,
      f"included {len(inc)}, uncovered {sorted(inc - covered)}, rows from non-included {sorted(set(rows.study) - inc)}")
bad_ph = [m for m, l, v in zip(phys.measure, phys["loc"], phys.value) if not same(get(json.loads(l)), v, 1e-9)]
check("V7b physics values re-read", not bad_ph, f"{len(phys)} values, mismatches {bad_ph[:3]}")

# ---------------------------------------------------------------- V6 report claims
cj = D / "claims.json"
rep = PROJ / "TF_ATLAS_RANKING_28_OCT_2026.md"
if cj.exists() and rep.exists():
    claims = json.loads(cj.read_text(encoding="utf-8"))
    text = rep.read_text(encoding="utf-8")
    bad_c = []
    for c in claims:
        if c["kind"] == "row":
            r = rows[rows.row_id == c["row_id"]]
            if len(r) != 1:
                bad_c.append((c["id"], "row"))
                continue
            v = r.iloc[0][c["field"]]
        elif c["kind"] == "rowx":
            r = rows[rows.row_id == c["row_id"]]
            v = json.loads(r.iloc[0]["x_oos"])[c["idx"]] if len(r) == 1 else None
        elif c["kind"] == "chance":
            r = ch[(ch.study == c["study"]) & (ch.tf == c["tf"])]
            v = r.iloc[0][c["field"]] if len(r) == 1 else None
        elif c["kind"] == "phys":
            r = phys[(phys.tf == c["tf"]) & (phys.measure == c["measure"])]
            v = r.iloc[0]["value"] if len(r) == 1 else None
        elif c["kind"] == "inventory":
            v = len(inv) if c["which"] == "all" else sum(1 for r in inv if r["include"] == c["which"])
        elif c["kind"] == "sources":
            v = len(src)
        elif c["kind"] == "chance_agg":
            gg = ch[ch.study.isin(c["studies"])][c["field"]]
            v = getattr(gg, c["fn"])()
        elif c["kind"] == "count":
            q = rows.query(c["query"]) if c.get("query") else rows
            v = len(q)
        else:
            v = None
        if v is None or not same(float(v) * c.get("mult", 1.0), c["num"], c.get("tol", 1e-9)) or c["text"] not in text:
            bad_c.append((c["id"], v, c["num"], c["text"] in text))
    check("V6 report claims", not bad_c, f"{len(claims)} claims, bad {bad_c[:5]}")
else:
    print("INFO  V6 skipped (claims.json / report not written yet)")

n_fail = res.count(False)
print(f"\nTOTAL {len(res)} checks, {len(res) - n_fail} PASS, {n_fail} FAIL -> {'ALL PASS' if n_fail == 0 else 'FAIL'}")
sys.exit(1 if n_fail else 0)
