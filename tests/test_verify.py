"""The publish gate. Each test breaks a real build in one way and expects a
problem to be reported -- a gate that cannot fail is not a gate.
"""

import sqlite3

import pytest

from aeronav_db.verify import verify_database

GOOD_AIRPORTS = [
    ("DFW", 32.897233, -97.037695, "DALLAS-FORT WORTH INTL", "airport", "iata", "nasr"),
    ("KDFW", 32.897233, -97.037695, "DFW INTL", "airport", "icao", "nasr"),
    ("DEN", 39.861667, -104.673167, "DENVER INTL", "airport", "iata", "nasr"),
    ("ANC", 61.174085, -149.998138, "TED STEVENS", "airport", "iata", "nasr"),
    ("LHR", 51.470748, -0.459909, "Heathrow", "large_airport", "iata", "ourairports"),
    ("EGLL", 51.470748, -0.459909, "Heathrow", "large_airport", "icao", "ourairports"),
    ("SYD", -33.946098, 151.177002, "Sydney", "large_airport", "iata", "ourairports"),
]


def build_database(
    path,
    *,
    airports=None,
    nasr_filler=13_000,
    ourairports_filler=13_000,
    navaids=1_200,
    fixes=60_000,
    metadata=None,
    size_padding=1_200_000,
):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE airports (code TEXT PRIMARY KEY, lat REAL, lon REAL,
            name TEXT, kind TEXT, code_type TEXT, source TEXT);
        CREATE TABLE navaids (ident TEXT, nav_type TEXT, name TEXT, lat REAL,
            lon REAL, frequency TEXT, source TEXT);
        CREATE TABLE fixes (fix_id TEXT, lat REAL, lon REAL, use_code TEXT,
            artcc_high TEXT, artcc_low TEXT, state_code TEXT, source TEXT);
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE padding (blob BLOB);
        """
    )
    connection.executemany(
        "INSERT INTO airports VALUES (?, ?, ?, ?, ?, ?, ?)",
        GOOD_AIRPORTS if airports is None else airports,
    )
    # Filler rows so the row-count floors are met without listing 25k airports.
    connection.executemany(
        "INSERT INTO airports VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (f"N{index:05d}", 40.0, -100.0, "filler", "airport", "faa", "nasr")
            for index in range(nasr_filler)
        ],
    )
    connection.executemany(
        "INSERT INTO airports VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (f"O{index:05d}", 40.0, -100.0, "filler", "small_airport", "iata",
             "ourairports")
            for index in range(ourairports_filler)
        ],
    )
    connection.executemany(
        "INSERT INTO navaids VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(f"V{i}", "VOR", "filler", 40.0, -100.0, "112.3", "nasr")
         for i in range(navaids)],
    )
    connection.executemany(
        "INSERT INTO fixes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(f"FIX{i:05d}", 40.0, -100.0, "RP", "ZNY", "ZNY", "NY", "nasr")
         for i in range(fixes)],
    )
    connection.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        (metadata or {
            "airac_cycle": "2026-07-09",
            "schema_version": "1",
            "sources": "FAA NASR; OurAirports",
        }).items(),
    )
    if size_padding:
        connection.execute("INSERT INTO padding VALUES (?)", (b"\0" * size_padding,))
    connection.commit()
    connection.close()
    return path


def test_a_healthy_build_passes(tmp_path) -> None:
    database = build_database(tmp_path / "navigation.sqlite3")

    assert verify_database(database) == []


def test_missing_file_is_reported(tmp_path) -> None:
    problems = verify_database(tmp_path / "absent.sqlite3")

    assert any("does not exist" in problem for problem in problems)


def test_a_file_that_is_not_a_database_is_reported(tmp_path) -> None:
    corrupt = tmp_path / "navigation.sqlite3"
    corrupt.write_bytes(b"definitely not sqlite" * 100_000)

    assert verify_database(corrupt)


def test_a_truncated_database_is_reported(tmp_path) -> None:
    """A well-formed but near-empty file -- what a cut-short download leaves."""
    database = build_database(
        tmp_path / "navigation.sqlite3",
        nasr_filler=0,
        ourairports_filler=0,
        navaids=0,
        fixes=0,
        size_padding=0,
    )

    assert any("implausibly small" in problem for problem in verify_database(database))


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"fixes": 10}, "fixes"),
        ({"navaids": 10}, "navaids"),
        ({"nasr_filler": 10, "ourairports_filler": 10}, "airports"),
    ],
)
def test_empty_or_thin_tables_are_reported(tmp_path, kwargs, expected) -> None:
    database = build_database(tmp_path / "navigation.sqlite3", **kwargs)

    assert any(expected in problem for problem in verify_database(database))


def test_losing_a_whole_source_layer_is_reported(tmp_path) -> None:
    """Row counts alone would still look healthy -- this is the check that
    catches a build that silently dropped NASR or OurAirports."""
    database = build_database(
        tmp_path / "navigation.sqlite3", ourairports_filler=0, airports=GOOD_AIRPORTS
    )

    assert any("ourairports" in problem for problem in verify_database(database))


def test_a_missing_canary_airport_is_reported(tmp_path) -> None:
    without_heathrow = [row for row in GOOD_AIRPORTS if row[0] != "LHR"]
    database = build_database(tmp_path / "navigation.sqlite3",
                              airports=without_heathrow)

    assert any("LHR" in problem for problem in verify_database(database))


def test_a_canary_airport_in_the_wrong_place_is_reported(tmp_path) -> None:
    """Catches a lat/lon swap or a sign error, which row counts never would."""
    swapped = [
        (row[0], row[2], row[1], *row[3:]) if row[0] == "DFW" else row
        for row in GOOD_AIRPORTS
    ]
    database = build_database(tmp_path / "navigation.sqlite3", airports=swapped)

    assert any("DFW" in problem for problem in verify_database(database))


def test_missing_metadata_is_reported(tmp_path) -> None:
    database = build_database(
        tmp_path / "navigation.sqlite3",
        metadata={"schema_version": "1", "sources": "test"},
    )

    assert any("airac_cycle" in problem for problem in verify_database(database))
