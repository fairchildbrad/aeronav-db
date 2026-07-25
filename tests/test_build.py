"""Merge and parsing rules, driven by small synthetic source rows. No network."""

import sqlite3

from aeronav_db import build


def ourairports_row(**overrides) -> dict[str, str]:
    row = {
        "ident": "KDFW",
        "type": "large_airport",
        "name": "Dallas Fort Worth International Airport",
        "latitude_deg": "32.8968",
        "longitude_deg": "-97.0380",
        "iso_country": "US",
        "icao_code": "KDFW",
        "iata_code": "DFW",
    }
    row.update(overrides)
    return row


def nasr_row(**overrides) -> dict[str, str]:
    row = {
        "ARPT_ID": "DFW",
        "ICAO_ID": "KDFW",
        "ARPT_NAME": "DALLAS-FORT WORTH INTL",
        "SITE_TYPE_CODE": "A",
        "ARPT_STATUS": "O",
        "LAT_DECIMAL": "32.89723305",
        "LONG_DECIMAL": "-97.03769472",
    }
    row.update(overrides)
    return row


def as_dict(rows) -> dict[str, tuple]:
    return {row[0]: row for row in rows}


# --- Source hierarchy -----------------------------------------------------


def test_nasr_overrides_ourairports_for_the_same_code() -> None:
    airports = as_dict(build.build_airports([ourairports_row()], [nasr_row()]))

    assert airports["DFW"][1] == 32.897233
    assert airports["DFW"][6] == "nasr"
    assert airports["KDFW"][6] == "nasr"


def test_ourairports_supplies_airports_nasr_does_not_have() -> None:
    heathrow = ourairports_row(
        ident="EGLL",
        icao_code="EGLL",
        iata_code="LHR",
        name="London Heathrow Airport",
        latitude_deg="51.4706",
        longitude_deg="-0.4619",
        iso_country="GB",
    )

    airports = as_dict(build.build_airports([heathrow], [nasr_row()]))

    assert airports["LHR"][6] == "ourairports"
    assert airports["EGLL"][6] == "ourairports"
    assert airports["DFW"][6] == "nasr"


def test_nasr_wins_regardless_of_row_order() -> None:
    """Precedence must come from the source, not from who was inserted first."""
    forward = as_dict(build.build_airports([ourairports_row()], [nasr_row()]))
    # Same inputs, but the OurAirports record is a "better" type than the NASR
    # one would suggest -- NASR must still win.
    reverse = as_dict(
        build.build_airports(
            [ourairports_row(type="large_airport")],
            [nasr_row(SITE_TYPE_CODE="H")],
        )
    )

    assert forward["DFW"][6] == "nasr"
    assert reverse["DFW"][6] == "nasr"


# --- Exclusions -----------------------------------------------------------


def test_closed_nasr_airports_are_excluded() -> None:
    airports = as_dict(
        build.build_airports(
            [],
            [
                nasr_row(ARPT_ID="AL40", ICAO_ID="", ARPT_STATUS="CI"),
                nasr_row(ARPT_ID="XYZ1", ICAO_ID="", ARPT_STATUS="CP"),
                nasr_row(ARPT_ID="0J0", ICAO_ID="", ARPT_STATUS="O"),
            ],
        )
    )

    assert "AL40" not in airports
    assert "XYZ1" not in airports
    assert "0J0" in airports


def test_rows_without_usable_coordinates_are_skipped() -> None:
    airports = as_dict(
        build.build_airports(
            [
                ourairports_row(iata_code="AAA", ident="AAAA", icao_code="AAAA",
                                latitude_deg=""),
                ourairports_row(iata_code="BBB", ident="BBBB", icao_code="BBBB",
                                latitude_deg="not-a-number"),
                ourairports_row(iata_code="CCC", ident="CCCC", icao_code="CCCC",
                                latitude_deg="0", longitude_deg="0"),
                ourairports_row(iata_code="DDD", ident="DDDD", icao_code="DDDD",
                                latitude_deg="200", longitude_deg="10"),
            ],
            [],
        )
    )

    assert airports == {}


def test_small_ourairports_fields_without_iata_are_skipped() -> None:
    airports = as_dict(
        build.build_airports(
            [ourairports_row(type="small_airport", iata_code="", ident="XS01",
                             icao_code="")],
            [],
        )
    )

    assert airports == {}


# --- Code extraction ------------------------------------------------------


def test_faa_local_identifiers_are_kept() -> None:
    airports = as_dict(
        build.build_airports([], [nasr_row(ARPT_ID="0J0", ICAO_ID="")])
    )

    assert "0J0" in airports
    assert airports["0J0"][5] == "faa"


def test_icao_code_column_is_preferred_over_ident() -> None:
    row = ourairports_row(ident="XXXX", icao_code="EGLL", iata_code="LHR")

    airports = as_dict(build.build_airports([row], []))

    assert "EGLL" in airports
    assert "XXXX" not in airports


def test_navaids_and_fixes_parse() -> None:
    navaids = build.build_navaids(
        [
            {
                "NAV_ID": "IL",
                "NAV_TYPE": "NDB",
                "NAME": "SOMEWHERE",
                "LAT_DECIMAL": "41.0",
                "LONG_DECIMAL": "-88.0",
                "FREQ": "245",
            }
        ]
    )
    fixes = build.build_fixes(
        [
            {
                "FIX_ID": "BOSOX",
                "LAT_DECIMAL": "42.201886",
                "LONG_DECIMAL": "-71.627678",
                "FIX_USE_CODE": "RP",
                "ARTCC_ID_HIGH": "ZBW",
                "ARTCC_ID_LOW": "ZBW",
                "STATE_CODE": "MA",
            }
        ]
    )

    assert navaids[0][:3] == ("IL", "NDB", "SOMEWHERE")
    assert fixes[0][0] == "BOSOX"
    assert fixes[0][1] == 42.201886


# --- Output ---------------------------------------------------------------


def test_write_database_is_queryable_and_carries_metadata(tmp_path) -> None:
    database = tmp_path / "navigation.sqlite3"
    build.write_database(
        database,
        build.build_airports([ourairports_row()], [nasr_row()]),
        build.build_navaids([]),
        build.build_fixes([]),
        {"airac_cycle": "2026-07-09", "schema_version": "1", "sources": "test"},
    )

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        assert connection.execute(
            "SELECT lat FROM airports WHERE code = 'DFW'"
        ).fetchone()[0] == 32.897233
        assert dict(connection.execute("SELECT key, value FROM metadata"))[
            "airac_cycle"
        ] == "2026-07-09"
    finally:
        connection.close()


def test_build_is_deterministic(tmp_path) -> None:
    """Identical inputs must give a byte-identical file, or the published
    checksum tells consumers nothing about whether the data changed."""
    rows = (
        build.build_airports([ourairports_row()], [nasr_row()]),
        build.build_navaids([]),
        build.build_fixes([]),
    )
    metadata = {"airac_cycle": "2026-07-09", "schema_version": "1", "sources": "test"}

    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    build.write_database(first, *rows, metadata)
    build.write_database(second, *rows, metadata)

    assert build.sha256_of(first) == build.sha256_of(second)


def test_manifest_describes_the_database(tmp_path) -> None:
    database = tmp_path / "navigation.sqlite3"
    manifest_path = tmp_path / "manifest.json"
    build.write_database(
        database,
        build.build_airports([ourairports_row()], [nasr_row()]),
        [],
        [],
        {"airac_cycle": "2026-07-09", "schema_version": "1", "sources": "test"},
    )

    manifest = build.write_manifest(
        manifest_path,
        database,
        {
            "airac_cycle": "2026-07-09",
            "airport_count": "2",
            "navaid_count": "0",
            "fix_count": "0",
            "sources": "test",
        },
    )

    assert manifest["airac_cycle"] == "2026-07-09"
    assert manifest["database"]["sha256"] == build.sha256_of(database)
    assert manifest["database"]["size_bytes"] == database.stat().st_size
    assert manifest["counts"]["airports"] == 2
    assert manifest_path.exists()
