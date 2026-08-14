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

import sqlite3
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
}

# Floors, not targets. Current build: ~35,300 airports, ~1,600 navaids,
# ~70,000 fixes, ~1,500 airways over ~19,000 points, 54 boundaries over
# ~2,700 points.
MINIMUM_ROWS = {
    "airports": 25_000,
    "navaids": 1_000,
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
}
CANARY_TOLERANCE_DEGREES = 0.5

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
    for key in ("airac_cycle", "schema_version", "sources"):
        if not metadata.get(key):
            problems.append(f"metadata is missing {key}")

    # Both source layers must be present: a build that silently lost NASR
    # would still look healthy on row counts alone.
    sources = dict(
        connection.execute("SELECT source, count(*) FROM airports GROUP BY source")
    )
    for source in ("nasr", "ourairports"):
        if sources.get(source, 0) < 5_000:
            problems.append(
                f"airports from {source}: {sources.get(source, 0)}, "
                "expected at least 5000"
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

    problems.extend(_inspect_airways(connection))
    problems.extend(_inspect_boundaries(connection))
    return problems


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
    args = parser.parse_args(argv)

    problems = verify_database(Path(args.path))
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
