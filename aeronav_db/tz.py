"""Per-airport IANA time zone from a hand-maintained rules table.

    identity/tz/rules.csv      iso_country, region, county, tz, note
    identity/tz/overrides.csv  airport_id, tz, source (empty tz = sources
                               conflict; the airport stays unplaced)
    identity/tz/zone1970.tab   vendored from tzdata (TZDATA_VERSION beside it)
    identity/tz/partial_regions.csv  iso_country, region, zones, tzdata_quote:
                               regions that zone1970.tab splits between zones

The most specific rule wins: override, then (country, region, county), then
(country, region, *), then (country, *, *). Nothing is guessed. A country rule
is refused for a country with more than one zone; a region marked SPLIT places
only through county rules or overrides; anything unplaced gets tz NULL and a
reason in tz_unplaced. Zones are checked against the vendored zone1970.tab,
never the host's tzdata, so every runner resolves the same way.

    python -m aeronav_db.tz seed-rules   # (re)write the single-zone countries
    python -m aeronav_db.tz gate DB OURAIRPORTS_CSV   # Phase 3 done? (exit 1 if not)
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

TZ_DIR = Path(__file__).resolve().parent.parent / "identity" / "tz"
SPLIT = "SPLIT"
ANY = "*"
# NASR files US territories under COUNTRY_CODE US with their own STATE_CODE;
# ISO 3166 (and zone1970.tab) treat them as countries.
US_TERRITORIES = {"PR", "VI", "GU", "AS", "MP"}
PARTIAL_WORDS = ("most", "except", "part")
UNPLACED = (
    "multi_zone_country", "no_region", "no_county_match", "no_rule",
    "source_conflict",
)


class TzRulesError(Exception):
    pass


def tzdata_version(directory: Path = TZ_DIR) -> str:
    return (directory / "TZDATA_VERSION").read_text().strip()


def load_zone_tab(path: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """({country: [zones]}, {zone: comment}) from zone1970.tab."""
    by_country: dict[str, list[str]] = {}
    comments: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        zone = parts[2]
        comments[zone] = parts[3] if len(parts) > 3 else ""
        for country in parts[0].split(","):
            by_country.setdefault(country, []).append(zone)
    return by_country, comments


@dataclass
class Rules:
    zones: dict[str, list[str]]
    rules: dict[tuple[str, str, str], str] = field(default_factory=dict)
    overrides: dict[str, str] = field(default_factory=dict)
    partial: set[tuple[str, str]] = field(default_factory=set)

    def _load_partial(self, path: Path, comments: dict[str, str]) -> None:
        """Regions split between zones. Every non-US zone whose zone1970.tab
        comment says most/except/part must be named by some listed region, so
        the list stays complete as tzdata changes."""
        named: set[str] = set()
        if path.exists():
            with open(path, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    country = row["iso_country"].strip().upper()
                    region = row["region"].strip().upper()
                    where = f"partial_regions.csv {(country, region)}"
                    if country not in self.zones:
                        raise TzRulesError(f"{where}: not in zone1970.tab")
                    if not region.startswith(f"{country}-"):
                        raise TzRulesError(f"{where}: region must be ISO 3166-2")
                    if not (row.get("tzdata_quote") or "").strip():
                        raise TzRulesError(f"{where}: quote the zone1970.tab comment")
                    zones = row["zones"].split()
                    if region == f"{country}-*":
                        # The comment's qualifier is about the country, not
                        # a region ("most of Chile"); the quote says so.
                        if len(zones) != 1 or zones[0] not in self.zones[country]:
                            raise TzRulesError(f"{where}: one {country} zone")
                        named.update(zones)
                        continue
                    foreign = [z for z in zones if z not in self.zones[country]]
                    if len(zones) < 2 or foreign:
                        raise TzRulesError(
                            f"{where}: zones must be two or more {country} zones"
                        )
                    named.update(zones)
                    self.partial.add((country, region))
        for country, found in self.zones.items():
            if country in ("US", "AQ") or len(found) < 2:
                continue
            for zone in found:
                comment = comments.get(zone, "").lower()
                if any(w in comment for w in PARTIAL_WORDS) and zone not in named:
                    raise TzRulesError(
                        f"partial_regions.csv: {zone} ({comments[zone]!r}) covers "
                        f"part of a {country} region; list that region"
                    )

    @classmethod
    def load(cls, directory: Path = TZ_DIR) -> Rules:
        zones, comments = load_zone_tab(directory / "zone1970.tab")
        loaded = cls(zones)
        loaded._load_partial(directory / "partial_regions.csv", comments)
        with open(directory / "rules.csv", newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                loaded._add_rule(row, comments)
        overrides = directory / "overrides.csv"
        if overrides.exists():
            with open(overrides, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    loaded._add_override(row)
        loaded._check_splits()
        return loaded

    def _add_rule(self, row: dict[str, str], comments: dict[str, str]) -> None:
        country = row["iso_country"].strip().upper()
        region = row["region"].strip().upper() or ANY
        county = row["county"].strip().upper() or ANY
        tz = row["tz"].strip()
        note = (row.get("note") or "").strip()
        key = (country, region, county)
        where = f"rules.csv {key}"
        if country not in self.zones:
            raise TzRulesError(f"{where}: {country} is not in zone1970.tab")
        multi = len(self.zones[country]) > 1
        if tz == SPLIT:
            if region == ANY or county != ANY:
                raise TzRulesError(f"{where}: SPLIT marks a whole region")
        elif tz not in self.zones[country]:
            raise TzRulesError(f"{where}: {tz} is not a {country} zone in zone1970.tab")
        if region == ANY and county != ANY:
            raise TzRulesError(f"{where}: a county rule needs a region")
        if region == ANY and multi:
            raise TzRulesError(
                f"{where}: {country} has {len(self.zones[country])} zones; a "
                "country-wide rule would guess"
            )
        if multi and not note:
            raise TzRulesError(
                f"{where}: a rule in a multi-zone country cites a source"
            )
        if (country, region) in self.partial and county == ANY and tz != SPLIT:
            raise TzRulesError(
                f"{where}: {region} is split between zones (partial_regions.csv); "
                "mark it SPLIT and place by sub-region rows or cited overrides"
            )
        if key in self.rules and self.rules[key] != tz:
            raise TzRulesError(f"{where}: conflicting rules {self.rules[key]} / {tz}")
        self.rules[key] = tz

    def _add_override(self, row: dict[str, str]) -> None:
        airport_id = row["airport_id"].strip().upper()
        tz = row["tz"].strip()
        if not (row.get("source") or "").strip():
            raise TzRulesError(f"overrides.csv {airport_id}: no source cited")
        if tz == "":
            # A cited conflict between sources: the airport stays unplaced.
            pass
        elif not any(tz in zones for zones in self.zones.values()):
            raise TzRulesError(f"overrides.csv {airport_id}: {tz} not in zone1970.tab")
        if airport_id in self.overrides and self.overrides[airport_id] != tz:
            raise TzRulesError(f"overrides.csv {airport_id}: conflicting overrides")
        self.overrides[airport_id] = tz

    def _check_splits(self) -> None:
        for country, region in self.partial:
            if self.rules.get((country, region, ANY)) not in (SPLIT, None):
                raise TzRulesError(f"rules.csv {region}: listed partial, must be SPLIT")
        for (country, region, county), tz in self.rules.items():
            if county == ANY and tz != SPLIT:
                continue
            if county != ANY and self.rules.get((country, region, ANY)) not in (
                SPLIT, None
            ):
                raise TzRulesError(
                    f"rules.csv {(country, region, county)}: county rule under a "
                    "region rule; mark the region SPLIT instead"
                )

    def resolve(
        self, airport_id: str, country: str | None, region: str | None,
        county: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        """(tz, tz_basis, tz_unplaced)."""
        if airport_id.upper() in self.overrides:
            zone = self.overrides[airport_id.upper()]
            if zone == "":
                return None, None, "source_conflict"
            return zone, "override", None
        country = (country or "").upper()
        region = (region or "").upper()
        county = (county or "").upper()
        if country not in self.zones:
            return None, None, "no_rule"
        if region:
            if county and (country, region, county) in self.rules:
                return self.rules[(country, region, county)], "county", None
            regional = self.rules.get((country, region, ANY))
            if regional == SPLIT:
                return None, None, "no_county_match"
            if regional:
                return regional, "region", None
        national = self.rules.get((country, ANY, ANY))
        if national:
            return national, "country", None
        if len(self.zones[country]) > 1:
            return None, None, "no_region" if not region else "multi_zone_country"
        return None, None, "no_rule"


def placement_inputs(
    nasr_row: dict[str, str] | None, ourairports_row: dict[str, str] | None
) -> tuple[str | None, str | None, str | None]:
    """(iso_country, region, county). NASR wins where attached."""
    if nasr_row is not None:
        country = (nasr_row.get("COUNTRY_CODE") or "").strip().upper() or None
        state = (nasr_row.get("STATE_CODE") or "").strip().upper()
        county = (nasr_row.get("COUNTY_NAME") or "").strip().upper() or None
        if country == "US" and state in US_TERRITORIES:
            return state, None, None
        if country == "US" and state:
            return "US", f"US-{state}", county
        if country:
            return country, None, None
    if ourairports_row is not None:
        country = (ourairports_row.get("iso_country") or "").strip().upper() or None
        region = (ourairports_row.get("iso_region") or "").strip().upper() or None
        if region and region.endswith("-U-A"):  # OurAirports' "unassigned"
            region = None
        county = None
        if country != "US":
            # Outside the US the sub-region key is OurAirports' municipality:
            # free text, often the city served (03-02 AC-3, AC-3a lint).
            county = (ourairports_row.get("municipality") or "").strip().upper() or None
        return country, region, county
    return None, None, None


def seed_rules(directory: Path = TZ_DIR) -> int:
    """Rewrite the single-zone country rows; hand rows are kept."""
    zones, _ = load_zone_tab(directory / "zone1970.tab")
    path = directory / "rules.csv"
    kept = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as handle:
            kept = [r for r in csv.DictReader(handle)
                    if r["note"] != "single-zone country (zone1970.tab)"]
    generated = [
        {"iso_country": country, "region": ANY, "county": ANY, "tz": found[0],
         "note": "single-zone country (zone1970.tab)"}
        for country, found in zones.items() if len(found) == 1
    ]
    rows = sorted(generated + kept,
                  key=lambda r: (r["iso_country"], r["region"], r["county"]))
    with open(path, "w", newline="", encoding="utf-8") as handle:
        columns = ["iso_country", "region", "county", "tz", "note"]
        writer = csv.DictWriter(handle, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(generated)


def load_unplaced_by_design(directory: Path = TZ_DIR) -> dict[str, str]:
    path = directory / "unplaced_by_design.csv"
    listed: dict[str, str] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                reason = (row.get("reason") or "").strip()
                if not reason:
                    raise TzRulesError(
                        f"unplaced_by_design.csv {row['airport_id']}: no reason"
                    )
                listed[row["airport_id"].strip().upper()] = reason
    return listed


def gate(
    db_path: str, ourairports_csv: str, directory: Path = TZ_DIR
) -> tuple[bool, list[str]]:
    """Phase 3 done (03-02 AC-1). Returns (passed, report lines)."""
    import sqlite3
    from collections import Counter

    with open(ourairports_csv, newline="", encoding="utf-8") as handle:
        scheduled = {r["id"] for r in csv.DictReader(handle)
                     if r.get("scheduled_service") == "yes"}
    by_design = load_unplaced_by_design(directory)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT airport_id, ourairports_id, iso_country, tz, tz_unplaced "
        "FROM airport_identity WHERE in_current_cycle = 1"
    ).fetchall()
    conn.close()
    multi, open_sched, placed, null = Counter(), Counter(), Counter(), Counter()
    for airport_id, oa_id, country, tz, reason in rows:
        country = country or "??"
        if tz:
            placed[country] += 1
            continue
        null[(country, reason)] += 1
        if reason == "multi_zone_country" and country != "AQ":
            multi[country] += 1
        if (oa_id is not None and str(oa_id) in scheduled
                and airport_id.upper() not in by_design and country != "AQ"):
            open_sched[country] += 1
    lines = [f"present {len(rows)}, placed {sum(placed.values())}, "
             f"NULL {sum(null.values())}"]
    lines += [f"FAIL item 1: {c} has {n} airports with multi_zone_country"
              for c, n in sorted(multi.items())]
    lines += [f"FAIL item 2: {c} has {n} scheduled airports unplaced and unlisted"
              for c, n in sorted(open_sched.items())]
    passed = not multi and not open_sched
    lines.append("gate PASS" if passed else "gate FAIL")
    return passed, lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 3 and args[0] == "gate":
        passed, lines = gate(args[1], args[2])
        print("\n".join(lines))
        return 0 if passed else 1
    if args == ["seed-rules"]:
        print(f"{seed_rules()} single-zone countries written")
        Rules.load()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
