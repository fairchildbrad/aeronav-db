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

REQUIRED_TABLES = {"airports", "navaids", "fixes", "metadata"}

# Floors, not targets. Current build: ~35,300 airports, ~1,600 navaids,
# ~70,000 fixes.
MINIMUM_ROWS = {
    "airports": 25_000,
    "navaids": 1_000,
    "fixes": 50_000,
}

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
