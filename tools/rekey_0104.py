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

import csv
import io
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# The 19 class-(i) unplaced_by_design rows (01-04-PLAN <ubd_merge_table>).
DROP = frozenset("""
    AP0024202 AP0024204 AP0024205 AP0024206 AP0024209 AP0024211 AP0024214
    AP0024220 AP0024239 AP0024240 AP0024241 AP0024250 AP0024259 AP0024260
    AP0024401 AP0024412 AP0024420 AP0029834 AP0029908
""".split())
# Named special cases (01-04-PLAN precondition (a)).
NAMED = {"AP0029892": "AP0029637", "AP0024177": "AP0019250"}


def load(path):
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    aliases = dict(connection.execute(
        "SELECT alias_id, airport_id FROM airport_aliases"))
    ids = {
        row[0]: row[1:]
        for row in connection.execute(
            "SELECT airport_id, nasr_site_no, nasr_site_type, ourairports_id, "
            "first_cycle FROM airport_identity")
    }
    iata = defaultdict(set)
    for airport, code, effective in connection.execute(
        "SELECT airport_id, code, effective_date FROM airport_codes "
        "WHERE scheme = 'iata'"
    ):
        iata[airport].add((code, effective))
    return aliases, ids, iata


def build_map(old_path, new_path):
    old_aliases, old, old_iata = load(old_path)
    new_aliases, new, new_iata = load(new_path)

    def survivor(airport):
        return new_aliases.get(airport, airport)

    by_site, by_oa_first = defaultdict(set), defaultdict(set)
    by_oa_any, by_iata = defaultdict(set), defaultdict(set)
    for airport, (site, site_type, oa, first) in new.items():
        if site:
            by_site[(site, site_type)].add(survivor(airport))
        if oa and not site:
            by_oa_first[(oa, first)].add(survivor(airport))
        if oa:
            by_oa_any[oa].add(survivor(airport))
        for key in new_iata[airport]:
            by_iata[key].add(survivor(airport))

    mapping = {}
    for airport, (site, site_type, oa, first) in old.items():
        if airport in NAMED:
            mapping[airport] = NAMED[airport]
            continue
        if site:
            found = by_site[(site, site_type)]
        else:
            found = (
                by_oa_first.get((oa, first), set())
                or by_oa_any.get(oa, set())
                or set().union(*(by_iata[key] for key in old_iata[airport]))
            )
        if len(found) != 1:
            sys.exit(f"REFUSED: {airport} {old[airport]} maps to {sorted(found)}")
        mapping[airport] = next(iter(found))

    targets = defaultdict(list)
    for airport, target in mapping.items():
        if airport not in old_aliases:
            targets[target].append(airport)
    kinds = {}
    for airport, target in mapping.items():
        if airport in old_aliases:
            kinds[airport] = "alias"
        elif airport in NAMED:
            kinds[airport] = "special"
        elif len(targets[target]) > 1:
            kinds[airport] = "merged"
        else:
            kinds[airport] = "one_to_one"
    return mapping, kinds, targets


def rekey_csv(mapping, name, drop=frozenset()):
    path = REPO / "identity" / "tz" / name
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))
    head, body = rows[0], rows[1:]
    out, seen, dropped = [head], {}, []
    for row in body:
        if row[0] in drop:
            dropped.append(row[0])
            continue
        target = mapping[row[0]]
        if target in seen:
            sys.exit(f"REFUSED: {name} collision {row[0]} and {seen[target]} "
                     f"-> {target}")
        seen[target] = row[0]
        out.append([target, *row[1:]])
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(out)
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return len(body), len(out) - 1, dropped


def main(argv):
    old_path, new_path, map_path = argv[1], argv[2], argv[3]
    mapping, kinds, targets = build_map(old_path, new_path)
    if "--apply" in argv[4:]:
        print("overrides", rekey_csv(mapping, "overrides.csv"))
        print("unplaced_by_design",
              rekey_csv(mapping, "unplaced_by_design.csv", DROP))
        verify = REPO / "aeronav_db" / "verify.py"
        text = verify.read_text()
        literals = re.findall(r"AP\d{7}", text)
        verify.write_text(
            re.sub(r"AP\d{7}", lambda m: mapping[m.group(0)], text))
        print("verify literals", len(literals),
              [(x, mapping[x]) for x in literals])
    with open(map_path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["old_airport_id", "new_airport_id", "kind"])
        for airport in sorted(mapping):
            writer.writerow([airport, mapping[airport], kinds[airport]])
    merges = sum(1 for olds in targets.values() if len(olds) > 1)
    print("map", len(mapping), Counter(kinds.values()), "merge targets", merges)


if __name__ == "__main__":
    main(sys.argv)
