#!/usr/bin/env python3
"""Compile the aeronav navigation database from its upstream sources.

Sources (both 100% public domain, so the compiled database carries no licensing
or copyleft encumbrance):

* **FAA NASR 28-Day Subscription** — the official source of truth for US
  airspace, published on the 28-day AIRAC cycle. A work of the US Government,
  public domain, free for commercial use with no attribution requirement.
  We read six subscriber files out of the nested ``CSV_Data`` archive:
  ``APT_BASE.csv`` (~19k landing facilities), ``NAV_BASE.csv`` (~1.6k radio
  navaids), ``FIX_BASE.csv`` (~70k named fixes / 5LNCs), ``AWY_BASE.csv`` and
  ``AWY_SEG_ALT.csv`` (~1.5k airways over ~19k points), and ``ARB_SEG.csv``
  (ARTCC and FIR boundary rings).
* **OurAirports** — nightly global CSV dumps released under CC0. Supplies the
  worldwide layer NASR does not cover, and is the only one of the two that
  carries IATA codes.

Merge rule: **NASR wins inside US airspace, OurAirports provides the global
fallback** — the national AIS is authoritative within its own jurisdiction.

The build is deterministic for a given SQLite version: rows are sorted and the
database is VACUUMed, so rebuilding from identical inputs on the same machine
gives a byte-identical file. Across SQLite versions it is not -- page layout and
the version field in the file header differ, so the same data can produce a
different checksum. A checksum change therefore means "this file differs", not
necessarily "the data changed". See README.md.

Usage::

    python -m aeronav_db.build                       # newest in-force cycle
    python -m aeronav_db.build --cycle 2026-08-06
    python -m aeronav_db.build --nasr-zip ./28DaySubscription.zip
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from aeronav_db.cycle import BROWSER_USER_AGENT, latest_available_cycle, nasr_url

_BROWSER_UA = BROWSER_USER_AGENT

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
OUTPUT_PATH = DIST_DIR / "navigation.sqlite3"
MANIFEST_PATH = DIST_DIR / "manifest.json"

# Schema version. Bump on any breaking change to table or column layout so a
# consumer can refuse a database it does not understand.
#
# 2: added airways, airway_points, boundaries and boundary_points.
SCHEMA_VERSION = "2"

IATA_RE = re.compile(r"^[A-Z]{3}$")
ICAO_RE = re.compile(r"^[A-Z]{4}$")
# FAA location identifiers are 3-4 alphanumerics (e.g. DFW, 0J0, 7TX6).
FAA_LID_RE = re.compile(r"^[A-Z0-9]{3,4}$")

# OurAirports airport types, most significant first. Used to break code
# collisions deterministically.
OURAIRPORTS_TYPE_PRIORITY = {
    "large_airport": 0,
    "medium_airport": 1,
    "small_airport": 2,
    "seaplane_base": 3,
    "balloonport": 4,
    "heliport": 5,
    "closed": 6,
}
UNKNOWN_TYPE_PRIORITY = 7

# NASR SITE_TYPE_CODE -> a readable kind, and its collision priority.
NASR_SITE_TYPES = {
    "A": ("airport", 0),
    "C": ("seaplane_base", 3),
    "G": ("gliderport", 4),
    "B": ("balloonport", 4),
    "U": ("ultralight", 5),
    "H": ("heliport", 5),
}

SCHEMA = """
CREATE TABLE airports (
    code       TEXT PRIMARY KEY,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    name       TEXT,
    kind       TEXT,
    code_type  TEXT NOT NULL,
    source     TEXT NOT NULL
);

CREATE TABLE navaids (
    ident      TEXT NOT NULL,
    nav_type   TEXT,
    name       TEXT,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    frequency  TEXT,
    source     TEXT NOT NULL
);
CREATE INDEX idx_navaids_ident ON navaids (ident);

CREATE TABLE fixes (
    fix_id     TEXT NOT NULL,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    use_code   TEXT,
    artcc_high TEXT,
    artcc_low  TEXT,
    state_code TEXT,
    source     TEXT NOT NULL
);
CREATE INDEX idx_fixes_fix_id ON fixes (fix_id);

-- An airway is an ordered list of points, so it needs two tables: one row
-- naming the airway and one row per point along it.
--
-- `location` is part of the key, not decoration. NASR scopes airway
-- identifiers to a region (C, A for Alaska, H for Hawaii), so two different
-- airways can share an identifier. Note that C is not CONUS-only: it also
-- carries the Pacific oceanic routes worked by Oakland, Guam and Honolulu.
CREATE TABLE airways (
    awy_id       TEXT NOT NULL,
    location     TEXT NOT NULL,
    designation  TEXT,
    regulatory   TEXT,
    point_count  INTEGER NOT NULL,
    source       TEXT NOT NULL,
    PRIMARY KEY (awy_id, location)
);

-- NASR gives airway points by name only, with no coordinates. Resolving each
-- name against navaids/fixes is done once here at build time rather than by
-- every consumer: it needs the disambiguation rules below, and getting it
-- wrong puts an airway across the wrong part of the country.
--
-- `lat`/`lon` are nullable because a handful of points resolve to nothing.
-- Keeping the row with NULL coordinates records that the airway continues
-- through a point we could not place, which a consumer can draw as a gap.
-- Dropping the row instead would silently join the two points either side.
CREATE TABLE airway_points (
    awy_id      TEXT NOT NULL,
    location    TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    point_id    TEXT NOT NULL,
    point_type  TEXT,
    lat         REAL,
    lon         REAL,
    artcc       TEXT,
    state_code  TEXT,
    PRIMARY KEY (awy_id, location, seq)
);
CREATE INDEX idx_airway_points_awy ON airway_points (awy_id, location, seq);

-- ARTCC and FIR boundaries. One boundary is a closed ring of points, and the
-- same centre publishes separate rings for its low, high and unlimited
-- strata, so altitude is part of the identity rather than an attribute.
CREATE TABLE boundaries (
    boundary_id  TEXT NOT NULL,
    name         TEXT,
    kind         TEXT NOT NULL,
    altitude     TEXT NOT NULL,
    point_count  INTEGER NOT NULL,
    source       TEXT NOT NULL,
    PRIMARY KEY (boundary_id, kind, altitude)
);

CREATE TABLE boundary_points (
    boundary_id TEXT NOT NULL,
    kind        TEXT NOT NULL,
    altitude    TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    description TEXT,
    PRIMARY KEY (boundary_id, kind, altitude, seq)
);
CREATE INDEX idx_boundary_points_ring
    ON boundary_points (boundary_id, kind, altitude, seq);

CREATE TABLE metadata (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL
);
"""

# NASR point types that name a radio navaid rather than a named fix. Used to
# decide which table to resolve an airway point against first.
NAVAID_POINT_TYPES = frozenset(
    {"VORTAC", "VOR/DME", "VOR", "NDB", "NDB/DME", "DME", "TACAN"}
)


def _download(url: str, description: str) -> bytes:
    print(f"downloading {description} ...", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
    with urllib.request.urlopen(request, timeout=900) as response:  # noqa: S310
        payload = response.read()
    print(f"  {len(payload) / 1e6:.1f} MB", flush=True)
    return payload


def _round(value: float) -> float:
    return round(value, 6)


def _parse_coordinates(
    latitude: str | None, longitude: str | None
) -> tuple[float, float] | None:
    try:
        lat = float(latitude or "")
        lon = float(longitude or "")
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if lat == 0.0 and lon == 0.0:
        return None
    return _round(lat), _round(lon)


def _read_csv(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


NASR_TABLES = (
    "APT_BASE.csv",
    "NAV_BASE.csv",
    "FIX_BASE.csv",
    "AWY_BASE.csv",
    "AWY_SEG_ALT.csv",
    "ARB_SEG.csv",
)


def extract_nasr_tables(nasr_zip: bytes) -> dict[str, list[dict[str, str]]]:
    """Pull the subscriber CSVs we consume out of the nested CSV archive."""
    outer = zipfile.ZipFile(io.BytesIO(nasr_zip))
    inner_names = [
        name
        for name in outer.namelist()
        if name.startswith("CSV_Data/") and name.lower().endswith(".zip")
    ]
    if not inner_names:
        raise SystemExit("NASR archive has no CSV_Data/*.zip payload")
    inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_names[0])))

    tables: dict[str, list[dict[str, str]]] = {}
    for wanted in NASR_TABLES:
        match = next(
            (n for n in inner.namelist() if n.rsplit("/", 1)[-1] == wanted), None
        )
        if match is None:
            raise SystemExit(f"NASR CSV archive is missing {wanted}")
        tables[wanted] = _read_csv(inner.read(match))
        print(f"  {wanted}: {len(tables[wanted])} rows", flush=True)
    return tables


def build_airports(
    ourairports_rows: list[dict[str, str]], nasr_rows: list[dict[str, str]]
) -> list[tuple[str, float, float, str | None, str | None, str, str]]:
    """Merge the global OurAirports layer with authoritative NASR US records.

    Returns rows of ``(code, lat, lon, name, kind, code_type, source)``.
    """
    # code -> (priority, tie_break, lat, lon, name, kind, code_type, source)
    chosen: dict[str, tuple[int, str, float, float, str | None, str, str, str]] = {}

    def offer(
        code: str,
        priority: int,
        tie_break: str,
        lat: float,
        lon: float,
        name: str | None,
        kind: str,
        code_type: str,
        source: str,
        authoritative: bool,
    ) -> None:
        existing = chosen.get(code)
        candidate = (priority, tie_break, lat, lon, name, kind, code_type, source)
        if existing is None:
            chosen[code] = candidate
            return
        # NASR always displaces OurAirports for the same code: inside US
        # airspace the national AIS is the source of truth.
        if authoritative and existing[7] != "nasr":
            chosen[code] = candidate
            return
        if authoritative == (existing[7] == "nasr") and candidate[:2] < existing[:2]:
            chosen[code] = candidate

    # --- Global layer: OurAirports (IATA + ICAO) --------------------------
    for row in ourairports_rows:
        airport_type = (row.get("type") or "").strip()
        iata = (row.get("iata_code") or "").strip().upper()
        has_iata = bool(IATA_RE.match(iata))
        if not has_iata and airport_type not in {"large_airport", "medium_airport"}:
            continue
        coords = _parse_coordinates(row.get("latitude_deg"), row.get("longitude_deg"))
        if coords is None:
            continue

        lat, lon = coords
        name = (row.get("name") or "").strip() or None
        priority = OURAIRPORTS_TYPE_PRIORITY.get(airport_type, UNKNOWN_TYPE_PRIORITY)
        ident = (row.get("ident") or "").strip().upper()

        if has_iata:
            offer(
                iata, priority, ident, lat, lon, name, airport_type, "iata",
                "ourairports", authoritative=False,
            )
        icao = next(
            (
                candidate
                for candidate in (
                    (row.get("icao_code") or "").strip().upper(),
                    ident,
                )
                if ICAO_RE.match(candidate)
            ),
            None,
        )
        if icao is not None:
            offer(
                icao, priority, ident, lat, lon, name, airport_type, "icao",
                "ourairports", authoritative=False,
            )

    # --- US layer: FAA NASR (FAA LID + ICAO), authoritative ---------------
    for row in nasr_rows:
        # 'O' = operational. 'CI'/'CP' are closed indefinitely/permanently and
        # must not resolve to a pin.
        if (row.get("ARPT_STATUS") or "").strip().upper() != "O":
            continue
        coords = _parse_coordinates(row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL"))
        if coords is None:
            continue

        lat, lon = coords
        name = (row.get("ARPT_NAME") or "").strip() or None
        site_type = (row.get("SITE_TYPE_CODE") or "").strip().upper()
        kind, priority = NASR_SITE_TYPES.get(site_type, ("unknown", 6))
        faa_lid = (row.get("ARPT_ID") or "").strip().upper()
        icao_id = (row.get("ICAO_ID") or "").strip().upper()
        tie_break = faa_lid or icao_id

        if FAA_LID_RE.match(faa_lid):
            code_type = "iata" if IATA_RE.match(faa_lid) else "faa"
            offer(
                faa_lid, priority, tie_break, lat, lon, name, kind, code_type,
                "nasr", authoritative=True,
            )
        if ICAO_RE.match(icao_id):
            offer(
                icao_id, priority, tie_break, lat, lon, name, kind, "icao",
                "nasr", authoritative=True,
            )

    return [
        (code, lat, lon, name, kind, code_type, source)
        for code, (_, _, lat, lon, name, kind, code_type, source) in sorted(
            chosen.items()
        )
    ]


def build_navaids(
    nasr_rows: list[dict[str, str]],
) -> list[tuple[str, str | None, str | None, float, float, str | None, str]]:
    navaids = []
    for row in nasr_rows:
        ident = (row.get("NAV_ID") or "").strip().upper()
        if not ident:
            continue
        coords = _parse_coordinates(row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL"))
        if coords is None:
            continue
        lat, lon = coords
        navaids.append(
            (
                ident,
                (row.get("NAV_TYPE") or "").strip() or None,
                (row.get("NAME") or "").strip() or None,
                lat,
                lon,
                (row.get("FREQ") or "").strip() or None,
                "nasr",
            )
        )
    navaids.sort(key=lambda entry: (entry[0], entry[3], entry[4]))
    return navaids


FixRow = tuple[
    str, float, float, str | None, str | None, str | None, str | None, str
]


def build_fixes(nasr_rows: list[dict[str, str]]) -> list[FixRow]:
    fixes = []
    for row in nasr_rows:
        fix_id = (row.get("FIX_ID") or "").strip().upper()
        if not fix_id:
            continue
        coords = _parse_coordinates(row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL"))
        if coords is None:
            continue
        lat, lon = coords
        fixes.append(
            (
                fix_id,
                lat,
                lon,
                (row.get("FIX_USE_CODE") or "").strip() or None,
                (row.get("ARTCC_ID_HIGH") or "").strip() or None,
                (row.get("ARTCC_ID_LOW") or "").strip() or None,
                (row.get("STATE_CODE") or "").strip() or None,
                "nasr",
            )
        )
    fixes.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    return fixes


AirwayRow = tuple[str, str, str | None, str | None, int, str]
AirwayPointRow = tuple[
    str, str, int, str, str | None, float | None, float | None, str | None, str | None
]


NavaidIndex = dict[str, list[tuple[float, float]]]
FixIndex = dict[str, list[tuple[float, float, str | None]]]


def _point_index(
    navaids: list[tuple], fixes: list[FixRow]
) -> tuple[NavaidIndex, FixIndex]:
    """Name -> coordinates lookups, built from the rows already compiled.

    Reusing the compiled rows rather than re-reading NASR keeps airway
    geometry consistent with the navaid and fix tables that ship alongside it.
    """
    navaid_index: NavaidIndex = {}
    for ident, _type, _name, lat, lon, _freq, _source in navaids:
        navaid_index.setdefault(ident, []).append((lat, lon))
    fix_index: FixIndex = {}
    for fix_id, lat, lon, _use, _high, _low, state, _source in fixes:
        fix_index.setdefault(fix_id, []).append((lat, lon, state))
    return navaid_index, fix_index


def _resolve_airway_point(
    point_id: str,
    point_type: str,
    state_code: str,
    navaid_index: dict[str, list[tuple[float, float]]],
    fix_index: dict[str, list[tuple[float, float, str | None]]],
) -> tuple[float, float] | None:
    """Coordinates for one named airway point, or None if it cannot be placed.

    A point is looked up in the table its type implies first, then the other,
    because a handful of names exist as both a navaid and a fix. Where a name
    still matches several rows, the segment's own state narrows it; failing
    that the first candidate in the already-sorted table is taken so the
    result is deterministic across builds rather than dictionary order.
    """
    navaid_matches = navaid_index.get(point_id) or []
    fix_matches = fix_index.get(point_id) or []

    if point_type in NAVAID_POINT_TYPES and navaid_matches:
        return navaid_matches[0]

    if fix_matches:
        if len(fix_matches) > 1 and state_code:
            same_state = [entry for entry in fix_matches if entry[2] == state_code]
            if same_state:
                return same_state[0][0], same_state[0][1]
        return fix_matches[0][0], fix_matches[0][1]

    if navaid_matches:
        return navaid_matches[0]
    return None


def build_airways(
    base_rows: list[dict[str, str]],
    segment_rows: list[dict[str, str]],
    navaids: list[tuple],
    fixes: list[FixRow],
) -> tuple[list[AirwayRow], list[AirwayPointRow], int]:
    """Airways and their resolved point geometry.

    Returns the airway rows, the point rows, and the number of points that
    could not be placed, which the caller reports so a resolution regression
    in a future cycle is visible in the build log rather than silent.
    """
    navaid_index, fix_index = _point_index(navaids, fixes)

    points: list[AirwayPointRow] = []
    counts: dict[tuple[str, str], int] = {}
    unresolved = 0

    ordered = sorted(
        segment_rows,
        key=lambda row: (
            (row.get("AWY_ID") or "").strip().upper(),
            (row.get("AWY_LOCATION") or "").strip().upper(),
            int((row.get("POINT_SEQ") or "0").strip() or 0),
        ),
    )
    for row in ordered:
        awy_id = (row.get("AWY_ID") or "").strip().upper()
        location = (row.get("AWY_LOCATION") or "").strip().upper()
        point_id = (row.get("FROM_POINT") or "").strip().upper()
        if not awy_id or not location or not point_id:
            continue
        try:
            seq = int((row.get("POINT_SEQ") or "").strip())
        except ValueError:
            continue

        point_type = (row.get("FROM_PT_TYPE") or "").strip()
        state_code = (row.get("STATE_CODE") or "").strip()
        coords = _resolve_airway_point(
            point_id, point_type, state_code, navaid_index, fix_index
        )
        if coords is None:
            unresolved += 1
        points.append(
            (
                awy_id,
                location,
                seq,
                point_id,
                point_type or None,
                coords[0] if coords else None,
                coords[1] if coords else None,
                (row.get("ARTCC") or "").strip() or None,
                state_code or None,
            )
        )
        counts[(awy_id, location)] = counts.get((awy_id, location), 0) + 1

    airways: list[AirwayRow] = []
    for row in base_rows:
        awy_id = (row.get("AWY_ID") or "").strip().upper()
        location = (row.get("AWY_LOCATION") or "").strip().upper()
        if not awy_id or not location:
            continue
        point_count = counts.get((awy_id, location), 0)
        # An airway with no segments has no geometry to draw, so it is not
        # carried into the database at all.
        if point_count == 0:
            continue
        airways.append(
            (
                awy_id,
                location,
                (row.get("AWY_DESIGNATION") or "").strip() or None,
                (row.get("REGULATORY") or "").strip() or None,
                point_count,
                "nasr",
            )
        )
    airways.sort(key=lambda entry: (entry[0], entry[1]))
    return airways, points, unresolved


BoundaryRow = tuple[str, str | None, str, str, int, str]
BoundaryPointRow = tuple[str, str, str, int, float, float, str | None]


def build_boundaries(
    segment_rows: list[dict[str, str]],
) -> tuple[list[BoundaryRow], list[BoundaryPointRow]]:
    """ARTCC and FIR boundary rings from ARB_SEG.

    ARB_SEG carries decimal coordinates directly, so unlike airways these need
    no name resolution.
    """
    points: list[BoundaryPointRow] = []
    names: dict[tuple[str, str, str], str | None] = {}
    counts: dict[tuple[str, str, str], int] = {}

    ordered = sorted(
        segment_rows,
        key=lambda row: (
            (row.get("LOCATION_ID") or "").strip().upper(),
            (row.get("TYPE") or "").strip().upper(),
            (row.get("ALTITUDE") or "").strip().upper(),
            int((row.get("POINT_SEQ") or "0").strip() or 0),
        ),
    )
    for row in ordered:
        boundary_id = (row.get("LOCATION_ID") or "").strip().upper()
        kind = (row.get("TYPE") or "").strip().upper()
        altitude = (row.get("ALTITUDE") or "").strip().upper()
        if not boundary_id or not kind or not altitude:
            continue
        try:
            seq = int((row.get("POINT_SEQ") or "").strip())
        except ValueError:
            continue
        coords = _parse_coordinates(row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL"))
        if coords is None:
            continue
        key = (boundary_id, kind, altitude)
        points.append(
            (
                boundary_id,
                kind,
                altitude,
                seq,
                coords[0],
                coords[1],
                (row.get("BNDRY_PT_DESCRIP") or "").strip() or None,
            )
        )
        counts[key] = counts.get(key, 0) + 1
        names.setdefault(key, (row.get("LOCATION_NAME") or "").strip() or None)

    boundaries: list[BoundaryRow] = []
    for key in sorted(counts):
        boundary_id, kind, altitude = key
        boundaries.append(
            (boundary_id, names.get(key), kind, altitude, counts[key], "nasr")
        )
    return boundaries, points


def write_database(
    path: Path,
    airports: list[tuple],
    navaids: list[tuple],
    fixes: list[tuple],
    airways: list[tuple],
    airway_points: list[tuple],
    boundaries: list[tuple],
    boundary_points: list[tuple],
    metadata: dict[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO airports "
            "(code, lat, lon, name, kind, code_type, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            airports,
        )
        connection.executemany(
            "INSERT INTO navaids "
            "(ident, nav_type, name, lat, lon, frequency, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            navaids,
        )
        connection.executemany(
            "INSERT INTO fixes "
            "(fix_id, lat, lon, use_code, artcc_high, artcc_low, state_code, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            fixes,
        )
        connection.executemany(
            "INSERT INTO airways "
            "(awy_id, location, designation, regulatory, point_count, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            airways,
        )
        connection.executemany(
            "INSERT INTO airway_points "
            "(awy_id, location, seq, point_id, point_type, lat, lon, "
            "artcc, state_code) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            airway_points,
        )
        connection.executemany(
            "INSERT INTO boundaries "
            "(boundary_id, name, kind, altitude, point_count, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            boundaries,
        )
        connection.executemany(
            "INSERT INTO boundary_points "
            "(boundary_id, kind, altitude, seq, lat, lon, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            boundary_points,
        )
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )
        connection.commit()
        # Deterministic, compact output so the committed binary only changes
        # when the data does.
        connection.execute("VACUUM")
        connection.commit()
    finally:
        connection.close()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    manifest_path: Path, database_path: Path, metadata: dict[str, str]
) -> dict[str, object]:
    """The document a consumer reads to decide whether to download.

    Deliberately small and stable: a client fetches this, compares `airac_cycle`
    and `sha256` against what it already has, and only pulls the database when
    they differ.
    """
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "airac_cycle": metadata["airac_cycle"],
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "database": {
            "filename": database_path.name,
            "size_bytes": database_path.stat().st_size,
            "sha256": sha256_of(database_path),
        },
        "counts": {
            "airports": int(metadata["airport_count"]),
            "navaids": int(metadata["navaid_count"]),
            "fixes": int(metadata["fix_count"]),
            "airways": int(metadata["airway_count"]),
            "airway_points": int(metadata["airway_point_count"]),
            "boundaries": int(metadata["boundary_count"]),
            "boundary_points": int(metadata["boundary_point_count"]),
        },
        "sources": metadata["sources"],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build(
    *,
    cycle: str | None = None,
    nasr_zip_path: str | None = None,
    ourairports_csv_path: str | None = None,
    output: Path = OUTPUT_PATH,
    manifest: Path = MANIFEST_PATH,
) -> dict[str, object]:
    resolved_cycle = cycle or latest_available_cycle().isoformat()

    if nasr_zip_path:
        nasr_zip = Path(nasr_zip_path).read_bytes()
    else:
        nasr_zip = _download(nasr_url_for(resolved_cycle), f"FAA NASR {resolved_cycle}")

    print("extracting NASR subscriber files ...", flush=True)
    nasr = extract_nasr_tables(nasr_zip)

    if ourairports_csv_path:
        ourairports_raw = Path(ourairports_csv_path).read_bytes()
    else:
        ourairports_raw = _download(OURAIRPORTS_URL, "OurAirports airports.csv")
    ourairports_rows = _read_csv(ourairports_raw)

    airports = build_airports(ourairports_rows, nasr["APT_BASE.csv"])
    navaids = build_navaids(nasr["NAV_BASE.csv"])
    fixes = build_fixes(nasr["FIX_BASE.csv"])
    airways, airway_points, unresolved = build_airways(
        nasr["AWY_BASE.csv"], nasr["AWY_SEG_ALT.csv"], navaids, fixes
    )
    boundaries, boundary_points = build_boundaries(nasr["ARB_SEG.csv"])

    nasr_airports = sum(1 for row in airports if row[6] == "nasr")
    metadata = {
        "airac_cycle": resolved_cycle,
        "airport_count": str(len(airports)),
        "navaid_count": str(len(navaids)),
        "fix_count": str(len(fixes)),
        "airway_count": str(len(airways)),
        "airway_point_count": str(len(airway_points)),
        "boundary_count": str(len(boundaries)),
        "boundary_point_count": str(len(boundary_points)),
        "sources": "FAA NASR 28-Day Subscription (public domain); "
        "OurAirports (CC0 public domain)",
        "generator": "aeronav_db.build",
        "schema_version": SCHEMA_VERSION,
    }

    write_database(
        output,
        airports,
        navaids,
        fixes,
        airways,
        airway_points,
        boundaries,
        boundary_points,
        metadata,
    )
    document = write_manifest(manifest, output, metadata)

    print(f"wrote {output} ({output.stat().st_size / 1e6:.1f} MB)")
    print(f"  airports:   {len(airports)} ({nasr_airports} from NASR)")
    print(f"  navaids:    {len(navaids)}")
    print(f"  fixes:      {len(fixes)}")
    print(
        f"  airways:    {len(airways)} "
        f"({len(airway_points)} points, {unresolved} unplaced)"
    )
    print(f"  boundaries: {len(boundaries)} ({len(boundary_points)} points)")
    print(f"  AIRAC:      {resolved_cycle}")
    print(f"  sha256:   {document['database']['sha256']}")  # type: ignore[index]
    return document


def nasr_url_for(cycle: str) -> str:
    from datetime import date as _date

    return nasr_url(_date.fromisoformat(cycle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the navigation database.")
    parser.add_argument(
        "--cycle",
        help="AIRAC effective date, YYYY-MM-DD (default: newest in-force cycle).",
    )
    parser.add_argument("--nasr-zip", help="Local 28-day NASR subscription zip.")
    parser.add_argument("--ourairports-csv", help="Local OurAirports airports.csv.")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    args = parser.parse_args(argv)

    build(
        cycle=args.cycle,
        nasr_zip_path=args.nasr_zip,
        ourairports_csv_path=args.ourairports_csv,
        output=Path(args.output),
        manifest=Path(args.manifest),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
