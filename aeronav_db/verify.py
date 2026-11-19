"""Sanity checks a built database must pass before it is published.

Consumers of this repo update themselves automatically. A broken build that
reaches a release is therefore not a nuisance — it propagates. These checks are
the gate: CI refuses to publish anything that fails them, and a consumer is free
to run the same checks on what it downloads before trusting it.

The thresholds are deliberately loose. They are here to catch a *broken* build
(empty table, truncated download, schema drift, coordinates parsed as strings),
not to police normal cycle-to-cycle variation.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import date
from pathlib import Path

REQUIRED_TABLES = {
    "airports",
    "navaids",
    "fixes",
    "airways",
    "airway_points",
    "boundaries",
    "boundary_points",
    "metadata",
    "airport_identity",
    "airport_codes",
    "airport_presence",
    "airport_aliases",
}

IDENTITY_METADATA = (
    "airport_id_next",
    "history_start",
    "previous_cycle",
    "previous_db_sha256",
)
AIRPORT_ID_GLOB = "AP[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
CYCLE_DAYS = 28
# One airport, reachable by both its IATA and ICAO code: the PBI -> DJT rename
# was the case that made the permanent id necessary. Either spelling may be
# current (sources switched at different cycles), but on any date the field's
# IATA and ICAO codes must name the same, single airport_id.
CANARY_IDENTITY = {"iata": ("DJT", "PBI"), "icao": ("KDJT", "KPBI")}

# Floors, not targets. Current build: ~35,300 airports, ~9,700 navaids,
# ~70,000 fixes, ~1,500 airways over ~19,000 points, 54 boundaries over
# ~2,700 points.
MINIMUM_ROWS = {
    "airports": 25_000,
    "navaids": 7_000,
    "fixes": 50_000,
    "airways": 1_000,
    "airway_points": 15_000,
    "boundaries": 40,
    "boundary_points": 2_000,
}

# Airway points are resolved by name against navaids and fixes, so this is the
# check that matters most for airways: a rename or a column shift upstream
# would leave the tables full but the geometry empty. The current build leaves
# 169 of 19,247 unplaced (0.9%).
MAXIMUM_UNPLACED_AIRWAY_FRACTION = 0.05

# Codes that must resolve in any usable build, spanning both source layers and
# both code systems. If these are missing, something is structurally wrong.
CANARY_AIRPORTS = {
    "DFW": (32.9, -97.0),
    "KDFW": (32.9, -97.0),
    "DEN": (39.9, -104.7),
    "ANC": (61.2, -150.0),
    "LHR": (51.5, -0.5),
    "EGLL": (51.5, -0.5),
    "SYD": (-33.9, 151.2),
    # Foreign IATA codes that collide with a US FAA local identifier. Each of
    # these silently resolved to a US field thousands of miles away until the
    # 2026-08-22 fix, because a NASR record displaced the IATA row on a shared
    # three-letter code. They are canaries precisely because the failure is
    # invisible until somebody flies there: the row exists, the name looks
    # plausible, and only the coordinates are wrong.
    "PUJ": (18.6, -68.4),  # Punta Cana -- was PAULDING NORTHWEST ATLANTA, GA
    "DUB": (53.4, -6.3),  # Dublin -- was DUBOIS MUNI, PA
    "CPT": (-34.0, 18.6),  # Cape Town -- was CLEBURNE RGNL, TX
    "AUH": (24.4, 54.7),  # Abu Dhabi -- was AURORA MUNI, OR
}
CANARY_TOLERANCE_DEGREES = 0.5

# Navaids that must resolve, spanning both source layers. A navaid identifier
# is only 2-3 characters and is reused worldwide -- `BIG` is a VORTAC in
# Alaska, a VOR/DME in Turkey and another outside London -- so each of these
# asserts that *some* row for the identifier stands in the right place, which
# is what a consumer disambiguating by position needs to be true.
CANARY_NAVAIDS = {
    "CRG": (30.3, -81.5),  # Craig VORTAC, Florida -- NASR
    "LAM": (51.6, 0.2),  # Lambourne VOR/DME, England -- OurAirports
    "NTM": (50.0, 6.5),  # Nattenheim VOR/DME, Germany -- OurAirports
}

# One airway and one boundary whose real-world geometry is well known, to prove
# the ordered geometry survived the build and not just the row counts. V1
# begins at the Craig VORTAC on the Florida coast; ZAB is Albuquerque Center.
CANARY_AIRWAY = ("V1", "C", "CRG", (30.3, -81.5))
CANARY_BOUNDARY = ("ZAB", "ARTCC", "HIGH", (28.0, 38.5, -115.0, -99.0))


def verify_database(path: Path) -> list[str]:
    """Return a list of problems. Empty means the build is publishable."""
    problems: list[str] = []

    if not path.exists():
        return [f"database does not exist: {path}"]
    if path.stat().st_size < 1_000_000:
        problems.append(f"database is implausibly small: {path.stat().st_size} bytes")

    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as error:
        return [f"cannot open database: {error}"]

    # sqlite3.connect does not touch the file, so a non-database only reveals
    # itself on the first statement. Every read below has to be guarded.
    try:
        problems.extend(_inspect(connection))
    except sqlite3.Error as error:
        problems.append(f"cannot read database: {error}")
    finally:
        connection.close()

    return problems


def _inspect(connection: sqlite3.Connection) -> list[str]:
    problems: list[str] = []

    integrity = connection.execute("PRAGMA quick_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        problems.append(f"integrity check failed: {integrity}")

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    missing = REQUIRED_TABLES - tables
    if missing:
        problems.append(f"missing tables: {sorted(missing)}")
        return problems

    for table, minimum in MINIMUM_ROWS.items():
        count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        if count < minimum:
            problems.append(f"{table}: {count} rows, expected at least {minimum}")

    metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    # `licence` and `disclaimer` are required, not optional: for a consumer who
    # fetched the bare .sqlite3 they are the only copy of the terms in existence.
    for key in (
        "airac_cycle",
        "schema_version",
        "sources",
        "licence",
        "disclaimer",
    ):
        if not metadata.get(key):
            problems.append(f"metadata is missing {key}")

    # Both source layers must be present in both merged tables: a build that
    # silently lost one would still look healthy on row counts alone.
    for table, floors in (
        ("airports", {"nasr": 5_000, "ourairports": 5_000}),
        ("navaids", {"nasr": 1_000, "ourairports": 5_000}),
    ):
        sources = dict(
            connection.execute(
                f"SELECT source, count(*) FROM {table} GROUP BY source"  # noqa: S608
            )
        )
        for source, minimum in floors.items():
            if sources.get(source, 0) < minimum:
                problems.append(
                    f"{table} from {source}: {sources.get(source, 0)}, "
                    f"expected at least {minimum}"
                )

    for code, (expected_lat, expected_lon) in CANARY_AIRPORTS.items():
        row = connection.execute(
            "SELECT lat, lon FROM airports WHERE code = ?", (code,)
        ).fetchone()
        if row is None:
            problems.append(f"canary airport {code} does not resolve")
            continue
        lat, lon = row
        if not isinstance(lat, float) or not isinstance(lon, float):
            problems.append(f"canary airport {code} has non-numeric coordinates")
            continue
        if (
            abs(lat - expected_lat) > CANARY_TOLERANCE_DEGREES
            or abs(lon - expected_lon) > CANARY_TOLERANCE_DEGREES
        ):
            problems.append(
                f"canary airport {code} is at ({lat}, {lon}), "
                f"expected near ({expected_lat}, {expected_lon})"
            )

    for ident, (expected_lat, expected_lon) in CANARY_NAVAIDS.items():
        rows = connection.execute(
            "SELECT lat, lon FROM navaids WHERE ident = ?", (ident,)
        ).fetchall()
        if not rows:
            problems.append(f"canary navaid {ident} does not resolve")
            continue
        if not any(
            abs(lat - expected_lat) <= CANARY_TOLERANCE_DEGREES
            and abs(lon - expected_lon) <= CANARY_TOLERANCE_DEGREES
            for lat, lon in rows
        ):
            problems.append(
                f"canary navaid {ident} has no row near "
                f"({expected_lat}, {expected_lon}); got {rows}"
            )

    problems.extend(_inspect_airways(connection))
    problems.extend(_inspect_boundaries(connection))
    identity_problems, _ = check_identity(connection)
    problems.extend(identity_problems)
    cycle = metadata.get("airac_cycle", "")
    holders = [
        set().union(*(_held_on(connection, scheme, code, cycle) for code in codes))
        for scheme, codes in CANARY_IDENTITY.items()
    ]
    if any(len(h) != 1 for h in holders) or holders[0] != holders[1]:
        problems.append(
            "canary identity: IATA DJT/PBI and ICAO KDJT/KPBI do not resolve "
            f"to one airport_id on {cycle}: {holders}"
        )
    if metadata.get("tzdata_version"):
        problems.extend(check_timezones(connection, cycle))
    return problems


# ICAO code -> the zone it must resolve to, in any build that places zones.
CANARY_TZ = {
    "KDJT": "America/New_York", "PHNL": "Pacific/Honolulu",
    "KELP": "America/Denver", "PANC": "America/Anchorage",
}


def check_timezones(connection: sqlite3.Connection, cycle: str) -> list[str]:
    """tz invariants, checked against the vendored zone1970.tab."""
    from aeronav_db import tz as tzmod

    problems: list[str] = []
    zones, _ = tzmod.load_zone_tab(tzmod.TZ_DIR / "zone1970.tab")
    known = {z for found in zones.values() for z in found}
    single_zone_of = {found[0]: c for c, found in zones.items() if len(found) == 1}
    rows = connection.execute(
        "SELECT airport_id, tz, tz_basis, tz_unplaced, iso_country "
        "FROM airport_identity"
    ).fetchall()
    for airport_id, zone, basis, unplaced, country in rows:
        if zone is not None and zone not in known:
            problems.append(f"{airport_id}: tz {zone} is not in zone1970.tab")
        if (zone is None) != (basis is None):
            problems.append(f"{airport_id}: tz and tz_basis disagree on NULL")
        if (zone is None) != (unplaced is not None):
            problems.append(
                f"{airport_id}: tz_unplaced must be set exactly when tz is NULL"
            )
        if unplaced is not None and unplaced not in tzmod.UNPLACED:
            problems.append(f"{airport_id}: unknown tz_unplaced {unplaced!r}")
        if basis == "country" and not single_zone_of.get(zone):
            # NASR files PR, VI, GU, AS and MP under US; their zone is placed
            # as the territory's, so the check is on the zone, not iso_country.
            problems.append(f"{airport_id}: country-basis {zone} is no single-zone "
                            f"country's zone ({country})")
    for code, expected in CANARY_TZ.items():
        holders = _held_on(connection, "icao", code, cycle)
        found = {
            row[0] for row in connection.execute(
                f"SELECT tz FROM airport_identity WHERE airport_id IN "  # noqa: S608
                f"({','.join('?' * len(holders))})", sorted(holders))
        } if holders else set()
        if found != {expected}:
            problems.append(
                f"canary tz: {code} resolves to {found}, expected {expected}"
            )
    more = [f"... {len(problems) - 50} more"] if len(problems) > 50 else []
    return problems[:50] + more


def timezone_notes(path: Path, previous: Path | None = None) -> list[str]:
    """Coverage of present airports, and the change in unplaced since PREV."""
    def counts(p: Path) -> tuple[int, int, list]:
        connection = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        try:
            columns = {r[1] for r in connection.execute(
                "PRAGMA table_info(airport_identity)")}
            if "tz_unplaced" not in columns:
                return 0, 0, []
            placed, unplaced = connection.execute(
                "SELECT SUM(tz IS NOT NULL), SUM(tz IS NULL) FROM airport_identity "
                "WHERE in_current_cycle = 1").fetchone()
            top = connection.execute(
                "SELECT iso_country, COUNT(*) FROM airport_identity "
                "WHERE in_current_cycle = 1 AND tz IS NULL GROUP BY 1 "
                "ORDER BY 2 DESC, 1 LIMIT 10").fetchall()
            return placed or 0, unplaced or 0, top
        finally:
            connection.close()

    placed, unplaced, top = counts(path)
    notes = [f"time zones: {placed} present airports placed, {unplaced} unplaced"]
    if top:
        notes.append("unplaced by country: " + ", ".join(f"{c} {n}" for c, n in top))
    if previous is not None:
        was = counts(previous)[1]
        notes.append(f"unplaced change since previous file: {unplaced - was:+d}")
    return notes


def _held_on(connection: sqlite3.Connection, scheme: str, code: str, day: str):
    return {
        row[0]
        for row in connection.execute(
            "SELECT COALESCE(a.airport_id, c.airport_id) FROM airport_codes c "
            "LEFT JOIN airport_aliases a ON a.alias_id = c.airport_id "
            "WHERE c.scheme = ? AND c.code = ? AND c.effective_date <= ? "
            "AND (c.valid_to IS NULL OR ? < c.valid_to)",
            (scheme, code, day, day),
        )
    }


def check_identity(connection: sqlite3.Connection) -> tuple[list[str], list[str]]:
    """Schema-3 identity invariants that hold for a single file.

    Returns (problems, notes). Notes are reported but never fail the build.
    """
    problems: list[str] = []
    notes: list[str] = []
    metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    for key in IDENTITY_METADATA:
        if key not in metadata:
            problems.append(f"metadata is missing {key}")
    cycle = metadata.get("airac_cycle", "")

    def count(sql: str, *args) -> int:
        return connection.execute(sql, args).fetchone()[0]

    bad_ids = count(
        "SELECT count(*) FROM (SELECT airport_id AS i FROM airport_identity "
        "UNION ALL SELECT alias_id FROM airport_aliases "
        "UNION ALL SELECT airport_id FROM airport_aliases) "
        "WHERE i IS NULL OR i NOT GLOB ?",
        AIRPORT_ID_GLOB,
    )
    if bad_ids:
        problems.append(f"{bad_ids} airport ids break the AP+7 digit shape")

    highest = connection.execute(
        "SELECT max(CAST(substr(airport_id, 3) AS INTEGER)) FROM airport_identity"
    ).fetchone()[0]
    try:
        next_id = int(metadata.get("airport_id_next", ""))
    except ValueError:
        problems.append("metadata airport_id_next is not a number")
    else:
        if highest is not None and next_id <= highest:
            problems.append(
                f"airport_id_next {next_id} is not above the highest id {highest}"
            )

    # Referential integrity: SQLite does not enforce foreign keys by default.
    for table in ("airport_codes", "airport_presence", "airport_aliases", "airports"):
        orphans = count(
            f"SELECT count(*) FROM {table} t WHERE t.airport_id IS NULL "  # noqa: S608
            "OR NOT EXISTS (SELECT 1 FROM airport_identity i "
            "WHERE i.airport_id = t.airport_id)"
        )
        if orphans:
            problems.append(f"{table}: {orphans} rows name no airport_identity row")
    orphan_aliases = count(
        "SELECT count(*) FROM airport_aliases a WHERE NOT EXISTS "
        "(SELECT 1 FROM airport_identity i WHERE i.airport_id = a.alias_id)"
    )
    if orphan_aliases:
        problems.append(f"{orphan_aliases} alias ids are not airport identities")

    chained = count(
        "SELECT count(*) FROM airport_aliases a "
        "JOIN airport_aliases b ON b.alias_id = a.airport_id"
    )
    if chained:
        problems.append(f"{chained} aliases point at another alias (not one hop)")

    mismatched = count(
        "SELECT count(*) FROM airport_identity i WHERE i.in_current_cycle != "
        "EXISTS (SELECT 1 FROM airport_presence p "
        "WHERE p.airport_id = i.airport_id AND p.valid_to IS NULL)"
    )
    if mismatched:
        problems.append(
            f"{mismatched} identities: in_current_cycle disagrees with presence"
        )

    backwards = count(
        "SELECT count(*) FROM (SELECT effective_date e, valid_to v FROM airport_codes "
        "UNION ALL SELECT effective_date, valid_to FROM airport_presence) "
        "WHERE v IS NOT NULL AND (v <= e OR v > ?)",
        cycle,
    )
    if backwards:
        problems.append(
            f"{backwards} intervals end before they start or after the cycle"
        )

    # One holder per FAA / ICAO code at any time.
    for scheme in ("faa", "icao"):
        doubled = connection.execute(
            "SELECT code, count(*) FROM airport_codes WHERE scheme = ? "
            "AND valid_to IS NULL GROUP BY code HAVING count(*) > 1 ORDER BY code",
            (scheme,),
        ).fetchall()
        if doubled:
            problems.append(
                f"{len(doubled)} {scheme} codes held by more than one airport now: "
                f"{[code for code, _ in doubled[:10]]}"
            )
        overlapping = connection.execute(
            "SELECT DISTINCT a.code FROM airport_codes a JOIN airport_codes b "
            "ON a.scheme = b.scheme AND a.code = b.code "
            "AND (a.airport_id, a.effective_date) < (b.airport_id, b.effective_date) "
            "WHERE a.scheme = ? "
            "AND a.effective_date < COALESCE(b.valid_to, '9999-12-31') "
            "AND b.effective_date < COALESCE(a.valid_to, '9999-12-31') "
            "ORDER BY a.code",
            (scheme,),
        ).fetchall()
        if overlapping:
            problems.append(
                f"{len(overlapping)} {scheme} codes have overlapping intervals: "
                f"{[row[0] for row in overlapping[:10]]}"
            )

    shared_iata = count(
        "SELECT count(*) FROM (SELECT code FROM airport_codes "
        "WHERE scheme = 'iata' AND valid_to IS NULL "
        "GROUP BY code HAVING count(DISTINCT airport_id) > 1)"
    )
    notes.append(f"IATA codes held by more than one present airport: {shared_iata}")

    previous_cycle = metadata.get("previous_cycle") or ""
    if previous_cycle and cycle:
        try:
            gap = (date.fromisoformat(cycle) - date.fromisoformat(previous_cycle)).days
        except ValueError:
            problems.append(f"bad previous_cycle {previous_cycle!r}")
        else:
            if gap != CYCLE_DAYS:
                notes.append(
                    f"WARNING: previous_cycle {previous_cycle} is {gap} days before "
                    f"{cycle}, not {CYCLE_DAYS}: a cycle was skipped and its "
                    "changes are dated to this one"
                )
    return problems, notes


def _rows(connection: sqlite3.Connection, sql: str) -> set[tuple]:
    return set(connection.execute(sql).fetchall())


def check_chain(
    new: sqlite3.Connection, previous: sqlite3.Connection, previous_sha256: str
) -> list[str]:
    """What cycle N may and may not do to cycle N-1's history."""
    problems: list[str] = []
    new_meta = dict(new.execute("SELECT key, value FROM metadata"))
    old_meta = dict(previous.execute("SELECT key, value FROM metadata"))
    cycle, old_cycle = new_meta.get("airac_cycle", ""), old_meta.get("airac_cycle", "")
    if not old_cycle < cycle:
        problems.append(f"cycle {cycle} does not follow previous {old_cycle}")
    if new_meta.get("previous_cycle") != old_cycle:
        problems.append(
            f"previous_cycle {new_meta.get('previous_cycle')!r} is not {old_cycle!r}"
        )
    if new_meta.get("previous_db_sha256") != previous_sha256:
        problems.append("previous_db_sha256 does not match the previous file")
    if new_meta.get("history_start") != old_meta.get("history_start"):
        problems.append("history_start changed")
    try:
        if int(new_meta["airport_id_next"]) < int(old_meta["airport_id_next"]):
            problems.append("airport_id_next went backwards")
    except (KeyError, ValueError):
        problems.append("airport_id_next missing or not a number")

    old_ids = _rows(previous, "SELECT airport_id FROM airport_identity")
    new_ids = _rows(new, "SELECT airport_id FROM airport_identity")
    if old_ids - new_ids:
        problems.append(f"{len(old_ids - new_ids)} previous airport ids are missing")
    old_aliases = _rows(previous, "SELECT alias_id FROM airport_aliases")
    if old_aliases - _rows(new, "SELECT alias_id FROM airport_aliases"):
        problems.append("a previous alias is no longer an alias")

    for table, key_columns, date_index in (
        ("airport_codes", "airport_id, scheme, code, effective_date, source", 3),
        ("airport_presence", "airport_id, effective_date", 1),
    ):
        sql = f"SELECT {key_columns}, valid_to FROM {table}"  # noqa: S608
        old_rows, new_rows = _rows(previous, sql), _rows(new, sql)
        closed = {r for r in old_rows if r[-1] is not None}
        if closed - new_rows:
            problems.append(
                f"{table}: {len(closed - new_rows)} closed intervals "
                "changed or vanished"
            )
        new_by_key = {r[:-1]: r[-1] for r in new_rows}
        for row in old_rows - closed:
            if row[:-1] not in new_by_key:
                problems.append(f"{table}: open interval {row[:-1]} vanished")
            elif new_by_key[row[:-1]] not in (None, cycle):
                problems.append(
                    f"{table}: open interval {row[:-1]} closed at "
                    f"{new_by_key[row[:-1]]}, not {cycle}"
                )
        old_keys = {r[:-1] for r in old_rows}
        backdated = [
            r for r in new_rows if r[:-1] not in old_keys and r[date_index] != cycle
        ]
        if backdated:
            problems.append(
                f"{table}: {len(backdated)} new intervals not dated {cycle}"
            )
    return problems


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_chain(path: Path, previous: Path) -> list[str]:
    try:
        new = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        old = sqlite3.connect(f"file:{previous}?mode=ro", uri=True)
    except sqlite3.Error as error:
        return [f"cannot open database: {error}"]
    try:
        return check_chain(new, old, sha256_file(previous))
    except sqlite3.Error as error:
        return [f"cannot read database: {error}"]
    finally:
        new.close()
        old.close()


def identity_notes(path: Path) -> list[str]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return check_identity(connection)[1]
    except sqlite3.Error:
        return []
    finally:
        connection.close()


def _inspect_airways(connection: sqlite3.Connection) -> list[str]:
    problems: list[str] = []

    total, unplaced = connection.execute(
        "SELECT count(*), sum(lat IS NULL) FROM airway_points"
    ).fetchone()
    if total:
        fraction = (unplaced or 0) / total
        if fraction > MAXIMUM_UNPLACED_AIRWAY_FRACTION:
            problems.append(
                f"airway points without coordinates: {unplaced} of {total} "
                f"({fraction:.1%}), expected at most "
                f"{MAXIMUM_UNPLACED_AIRWAY_FRACTION:.0%}"
            )

    # Every airway must have geometry, and every point must belong to a
    # declared airway. Either failing means the two tables disagree.
    orphans = connection.execute(
        "SELECT count(*) FROM airway_points p LEFT JOIN airways a "
        "ON a.awy_id = p.awy_id AND a.location = p.location "
        "WHERE a.awy_id IS NULL"
    ).fetchone()[0]
    if orphans:
        problems.append(f"airway points belonging to no airway: {orphans}")

    empty = connection.execute(
        "SELECT count(*) FROM airways a WHERE NOT EXISTS "
        "(SELECT 1 FROM airway_points p "
        "WHERE p.awy_id = a.awy_id AND p.location = a.location)"
    ).fetchone()[0]
    if empty:
        problems.append(f"airways with no points: {empty}")

    awy_id, location, first_point, (lat, lon) = CANARY_AIRWAY
    row = connection.execute(
        "SELECT point_id, lat, lon FROM airway_points "
        "WHERE awy_id = ? AND location = ? ORDER BY seq LIMIT 1",
        (awy_id, location),
    ).fetchone()
    if row is None:
        problems.append(f"canary airway {awy_id} does not resolve")
    elif row[0] != first_point:
        problems.append(
            f"canary airway {awy_id} starts at {row[0]}, expected {first_point}"
        )
    elif (
        row[1] is None
        or abs(row[1] - lat) > CANARY_TOLERANCE_DEGREES
        or abs(row[2] - lon) > CANARY_TOLERANCE_DEGREES
    ):
        problems.append(
            f"canary airway {awy_id} starts at ({row[1]}, {row[2]}), "
            f"expected near ({lat}, {lon})"
        )
    return problems


def _inspect_boundaries(connection: sqlite3.Connection) -> list[str]:
    problems: list[str] = []

    # FIR rings are the reason this table exists for non-US-domestic use; a
    # build carrying only ARTCC rings has lost half the point.
    kinds = dict(
        connection.execute("SELECT kind, count(*) FROM boundaries GROUP BY kind")
    )
    if not kinds.get("ARTCC"):
        problems.append("no ARTCC boundaries")
    if not any(kind for kind in kinds if "FIR" in kind):
        problems.append(f"no FIR boundaries; kinds present: {sorted(kinds)}")

    orphans = connection.execute(
        "SELECT count(*) FROM boundary_points p LEFT JOIN boundaries b "
        "ON b.boundary_id = p.boundary_id AND b.kind = p.kind "
        "AND b.altitude = p.altitude WHERE b.boundary_id IS NULL"
    ).fetchone()[0]
    if orphans:
        problems.append(f"boundary points belonging to no boundary: {orphans}")

    # A ring needs at least three points to enclose anything.
    degenerate = connection.execute(
        "SELECT count(*) FROM boundaries WHERE point_count < 3"
    ).fetchone()[0]
    if degenerate:
        problems.append(f"boundaries with fewer than three points: {degenerate}")

    boundary_id, kind, altitude, (min_lat, max_lat, min_lon, max_lon) = CANARY_BOUNDARY
    row = connection.execute(
        "SELECT min(lat), max(lat), min(lon), max(lon), count(*) "
        "FROM boundary_points WHERE boundary_id = ? AND kind = ? AND altitude = ?",
        (boundary_id, kind, altitude),
    ).fetchone()
    if not row or not row[4]:
        problems.append(f"canary boundary {boundary_id} does not resolve")
    elif not (
        min_lat <= row[0]
        and row[1] <= max_lat
        and min_lon <= row[2]
        and row[3] <= max_lon
    ):
        problems.append(
            f"canary boundary {boundary_id} spans "
            f"({row[0]}, {row[1]}, {row[2]}, {row[3]}), expected within "
            f"({min_lat}, {max_lat}, {min_lon}, {max_lon})"
        )
    return problems



def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify a built database.")
    parser.add_argument("path", help="Path to navigation.sqlite3")
    parser.add_argument(
        "--previous",
        help="The previous cycle's file: check that history was only extended.",
    )
    args = parser.parse_args(argv)

    problems = verify_database(Path(args.path))
    if args.previous:
        problems.extend(verify_chain(Path(args.path), Path(args.previous)))
    for note in identity_notes(Path(args.path)) if Path(args.path).exists() else []:
        print(note)
    if Path(args.path).exists():
        previous_path = Path(args.previous) if args.previous else None
        for note in timezone_notes(Path(args.path), previous_path):
            print(note)
    if problems:
        print("VERIFICATION FAILED")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"verification passed: {args.path}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
