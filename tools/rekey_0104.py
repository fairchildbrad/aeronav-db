"""01-04 one-off re-key: old airport_id -> renumbered airport_id, by source keys.

    python tools/rekey_0104.py OLD.sqlite3 NEW.sqlite3 MAP.csv [--apply]

OLD is the schema3 candidate (tz8, 61d4979b...), NEW the 2026-10-29 build from
the renumbered seed (2be3aa91...). Map rule (01-04-PLAN <rekey_revision>, plus
the APPLY deviation): NASR site key; else OA id + first_cycle among OA-only new
identities; else any new identity now carrying that OA id; else IATA
intervals (code, effective_date). Aliases resolve to survivors. Anything not
single-valued is refused unless named in NAMED. Without --apply only MAP.csv
is written; --apply also re-keys identity/tz/*.csv and verify.py literals.
"""
import csv, io, re, sqlite3, sys
from collections import defaultdict
T8, NEW, MAP = sys.argv[1], sys.argv[2], sys.argv[3]
APPLY = "--apply" in sys.argv[4:]
REPO = __file__.rsplit("/tools/", 1)[0]
DROP = set("AP0024202 AP0024204 AP0024205 AP0024206 AP0024209 AP0024211 AP0024214 AP0024220 AP0024239 AP0024240 AP0024241 AP0024250 AP0024259 AP0024260 AP0024401 AP0024412 AP0024420 AP0029834 AP0029908".split())
NAMED = {"AP0029892": "AP0029637", "AP0024177": "AP0019250"}  # PLAN precondition (a)

def load(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    al = dict(c.execute("SELECT alias_id, airport_id FROM airport_aliases"))
    ids = {r[0]: r[1:] for r in c.execute("SELECT airport_id, nasr_site_no, nasr_site_type, ourairports_id, first_cycle FROM airport_identity")}
    iata = defaultdict(set)
    for a, code, eff in c.execute("SELECT airport_id, code, effective_date FROM airport_codes WHERE scheme='iata'"):
        iata[a].add((code, eff))
    return c, al, ids, iata

_, oal, o, oiata = load(T8)
_, nal, n, niata = load(NEW)
surv = lambda al, a: al.get(a, a)
by_oa_any = defaultdict(set); by_site = defaultdict(set); by_oa_first = defaultdict(set); by_iata = defaultdict(set)
for a, (s, t, oa, first) in n.items():
    if s: by_site[(s, t)].add(surv(nal, a))
    if oa and not s: by_oa_first[(oa, first)].add(surv(nal, a))
    if oa: by_oa_any[oa].add(surv(nal, a))
    for k in niata[a]: by_iata[k].add(surv(nal, a))
mapping, kinds = {}, {}
for a, (s, t, oa, first) in o.items():
    if a in NAMED:
        mapping[a] = NAMED[a]; continue
    if s: c = by_site[(s, t)]
    else:
        c = by_oa_first.get((oa, first), set()) or by_oa_any.get(oa, set()) or set().union(set(), *(by_iata[k] for k in oiata[a]))
    if len(c) != 1:
        sys.exit(f"REFUSED: {a} {o[a]} maps to {sorted(c)}")
    mapping[a] = next(iter(c))
# aliases in tz8 map through their survivor
for a in o:
    mapping[a] = mapping[a]
targets = defaultdict(list)
for a, b in mapping.items():
    if a not in oal: targets[b].append(a)
for a, b in mapping.items():
    if a in oal: kinds[a] = "alias"
    elif a in NAMED: kinds[a] = "special"
    elif len(targets[b]) > 1: kinds[a] = "merged"
    else: kinds[a] = "one_to_one"

def rekey_csv(name, drop=()):
    path = f"{REPO}/identity/tz/{name}"
    text = open(path, encoding="utf-8").read()
    rows = list(csv.reader(io.StringIO(text)))
    head, body = rows[0], rows[1:]
    out, seen, dropped = [head], {}, []
    for r in body:
        if r[0] in drop: dropped.append(r[0]); continue
        new = mapping[r[0]]
        if new in seen: sys.exit(f"REFUSED: {name} collision {r[0]} and {seen[new]} -> {new}")
        seen[new] = r[0]; out.append([new] + r[1:])
    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(out)
    open(path, "w", encoding="utf-8").write(buf.getvalue())
    return len(body), len(out) - 1, dropped

if APPLY:
    print("overrides", rekey_csv("overrides.csv"))
    print("unplaced_by_design", rekey_csv("unplaced_by_design.csv", DROP))
    vp = f"{REPO}/aeronav_db/verify.py"; v = open(vp).read()
    lits = re.findall(r"AP\d{7}", v)
    open(vp, "w").write(re.sub(r"AP\d{7}", lambda m: mapping[m.group(0)], v))
    print("verify literals", len(lits), [(x, mapping[x]) for x in lits])
with open(MAP, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["old_airport_id", "new_airport_id", "kind"])
    for a in sorted(mapping): w.writerow([a, mapping[a], kinds[a]])
from collections import Counter
print("map", len(mapping), Counter(kinds.values()), "merge targets", sum(1 for v in targets.values() if len(v) > 1))
