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


# --- Code collisions between a US FAA LID and a foreign IATA code ----------


def oa_airport(**overrides) -> dict[str, str]:
    row = {
        "ident": "MDPC",
        "type": "large_airport",
        "name": "Punta Cana International Airport",
        "latitude_deg": "18.567093",
        "longitude_deg": "-68.364558",
        "iata_code": "PUJ",
        "icao_code": "MDPC",
    }
    row.update(overrides)
    return row


def nasr_airport(**overrides) -> dict[str, str]:
    row = {
        "ARPT_ID": "PUJ",
        "ICAO_ID": "KPUJ",
        "ARPT_NAME": "PAULDING NORTHWEST ATLANTA",
        "SITE_TYPE_CODE": "A",
        "ARPT_STATUS": "O",
        "LAT_DECIMAL": "33.912043",
        "LONG_DECIMAL": "-84.940619",
    }
    row.update(overrides)
    return row


def test_a_us_identifier_does_not_displace_a_distant_foreign_iata_code() -> None:
    """A three-letter FAA LID collides with a foreign IATA code 512 times in
    the 2026-08-06 cycle. The two records are not one airport described twice,
    so NASR's authority over US airspace does not extend to taking the code --
    this put Punta Cana at a field in Georgia, and Dublin at DUBOIS MUNI."""
    rows = {
        row[0]: row
        for row in build.build_airports([oa_airport()], [nasr_airport()])
    }

    assert rows["PUJ"][3] == "Punta Cana International Airport"
    assert rows["PUJ"][6] == "ourairports"
    # The US field is not lost -- it keeps its own ICAO identifier.
    assert rows["KPUJ"][3] == "PAULDING NORTHWEST ATLANTA"


def test_nasr_still_displaces_ourairports_for_the_same_field() -> None:
    """The rule that NASR wins inside US airspace is intact where it applies:
    the same airport described by both sources takes the FAA's coordinates."""
    rows = {
        row[0]: row
        for row in build.build_airports(
            [
                oa_airport(
                    ident="KDFW", iata_code="DFW", icao_code="KDFW",
                    name="Dallas Fort Worth International Airport",
                    latitude_deg="32.8968", longitude_deg="-97.0380",
                )
            ],
            [
                nasr_airport(
                    ARPT_ID="DFW", ICAO_ID="KDFW", ARPT_NAME="DALLAS-FORT WORTH INTL",
                    LAT_DECIMAL="32.896828", LONG_DECIMAL="-97.037997",
                )
            ],
        )
    }

    assert rows["DFW"][3] == "DALLAS-FORT WORTH INTL"
    assert rows["DFW"][6] == "nasr"


def test_distance_decides_the_collision_not_the_source() -> None:
    """Just inside the threshold NASR wins; well outside it does not."""
    near = {
        row[0]: row
        for row in build.build_airports(
            [oa_airport(iata_code="XYZ", latitude_deg="33.95", longitude_deg="-84.94")],
            [nasr_airport(ARPT_ID="XYZ")],
        )
    }
    assert near["XYZ"][6] == "nasr"

    far = {
        row[0]: row
        for row in build.build_airports(
            [oa_airport(iata_code="XYZ", latitude_deg="18.56", longitude_deg="-68.36")],
            [nasr_airport(ARPT_ID="XYZ")],
        )
    }
    assert far["XYZ"][6] == "ourairports"


# --- Worldwide navaid layer ------------------------------------------------


def nasr_navaid(**overrides) -> dict[str, str]:
    row = {
        "NAV_ID": "CRG",
        "NAV_TYPE": "VORTAC",
        "NAME": "CRAIG",
        "LAT_DECIMAL": "30.338879",
        "LONG_DECIMAL": "-81.513611",
        "FREQ": "114.5",
    }
    row.update(overrides)
    return row


def oa_navaid(**overrides) -> dict[str, str]:
    row = {
        "ident": "LAM",
        "type": "VOR-DME",
        "name": "Lambourne",
        "frequency_khz": "115600",
        "latitude_deg": "51.646",
        "longitude_deg": "0.151666",
        "iso_country": "GB",
    }
    row.update(overrides)
    return row


def test_ourairports_navaids_extend_the_nasr_layer() -> None:
    navaids = build.build_navaids([nasr_navaid()], [oa_navaid()])

    assert [(row[0], row[6]) for row in navaids] == [
        ("CRG", "nasr"),
        ("LAM", "ourairports"),
    ]


def test_ourairports_navaid_types_are_spelled_the_nasr_way() -> None:
    """A consumer filtering on nav_type must not need to know the source."""
    navaids = build.build_navaids([], [oa_navaid(type="VOR-DME")])
    assert navaids[0][1] == "VOR/DME"

    navaids = build.build_navaids([], [oa_navaid(type="NDB-DME")])
    assert navaids[0][1] == "NDB/DME"

    navaids = build.build_navaids([], [oa_navaid(type="VORTAC")])
    assert navaids[0][1] == "VORTAC"


def test_vhf_navaid_frequencies_are_converted_to_megahertz() -> None:
    """OurAirports publishes kHz throughout; NASR uses MHz above the NDB band."""
    vhf = build.build_navaids([], [oa_navaid(frequency_khz="115600")])
    assert vhf[0][5] == "115.6"
    # Two decimals survive: VHF nav spacing is 50 kHz.
    half = build.build_navaids([], [oa_navaid(frequency_khz="114950")])
    assert half[0][5] == "114.95"
    # NDBs are already in the units NASR publishes, so they pass through.
    ndb = build.build_navaids([], [oa_navaid(type="NDB", frequency_khz="421")])
    assert ndb[0][5] == "421"


def test_ourairports_navaids_inside_us_airspace_are_dropped() -> None:
    """NASR is authoritative *and* complete there; OurAirports still lists aids
    the FAA has decommissioned, and a dead navaid that resolves is worse than
    one that is missing."""
    navaids = build.build_navaids(
        [],
        [
            oa_navaid(ident="ABB", type="VORTAC", name="Nabb", iso_country="US"),
            oa_navaid(ident="SJU", iso_country="PR"),
            oa_navaid(ident="UNZ", iso_country="GU"),
        ],
    )

    assert navaids == []


def test_a_navaid_nasr_already_carries_is_not_duplicated() -> None:
    """NASR holds some Canadian border aids that OurAirports also lists."""
    navaids = build.build_navaids(
        [nasr_navaid(NAV_ID="YSO", LAT_DECIMAL="44.0", LONG_DECIMAL="-79.0")],
        [
            oa_navaid(
                ident="YSO",
                iso_country="CA",
                latitude_deg="44.1",
                longitude_deg="-79.1",
            )
        ],
    )

    assert [row[6] for row in navaids] == ["nasr"]


def test_a_shared_identifier_far_from_the_nasr_aid_is_kept() -> None:
    """`BIG` is a VORTAC in Alaska and an unrelated VOR/DME outside London.
    Collapsing them on identifier alone would lose the English one."""
    navaids = build.build_navaids(
        [nasr_navaid(NAV_ID="BIG", LAT_DECIMAL="64.0044", LONG_DECIMAL="-145.716")],
        [
            oa_navaid(
                ident="BIG",
                name="Biggin",
                iso_country="GB",
                latitude_deg="51.3308",
                longitude_deg="0.034811",
            )
        ],
    )

    assert len(navaids) == 2
    assert {row[6] for row in navaids} == {"nasr", "ourairports"}


def test_navaids_build_unchanged_without_the_worldwide_layer() -> None:
    """The OurAirports argument is optional, so an NASR-only build still works."""
    assert build.build_navaids([nasr_navaid()]) == build.build_navaids(
        [nasr_navaid()], []
    )


# --- Airways and boundaries -----------------------------------------------


def awy_segment(**overrides) -> dict[str, str]:
    row = {
        "AWY_ID": "V1",
        "AWY_LOCATION": "C",
        "POINT_SEQ": "10",
        "FROM_POINT": "CRG",
        "FROM_PT_TYPE": "VORTAC",
        "ARTCC": "ZJX",
        "STATE_CODE": "FL",
    }
    row.update(overrides)
    return row


def awy_base(**overrides) -> dict[str, str]:
    row = {
        "AWY_ID": "V1",
        "AWY_LOCATION": "C",
        "AWY_DESIGNATION": "V",
        "REGULATORY": "N",
    }
    row.update(overrides)
    return row


CRG_NAVAID = ("CRG", "VORTAC", "CRAIG", 30.338879, -81.509927, "114.5", "nasr")
BOSOX_FIX = ("BOSOX", 42.201886, -70.9, "RP", "ZBW", "ZBW", "MA", "nasr")


def test_airway_points_resolve_against_navaids_and_fixes() -> None:
    segments = [
        awy_segment(),
        awy_segment(
            POINT_SEQ="20", FROM_POINT="BOSOX", FROM_PT_TYPE="RP", STATE_CODE="MA"
        ),
    ]

    airways, points, unresolved = build.build_airways(
        [awy_base()], segments, [CRG_NAVAID], [BOSOX_FIX]
    )

    assert unresolved == 0
    assert [point[3] for point in points] == ["CRG", "BOSOX"]
    assert points[0][5] == 30.338879
    assert points[1][5] == 42.201886
    assert airways[0][4] == 2


def test_an_unresolvable_airway_point_is_kept_with_no_coordinates() -> None:
    """Dropping it instead would silently join the points either side."""
    segments = [
        awy_segment(),
        awy_segment(POINT_SEQ="20", FROM_POINT="NOSUCH", FROM_PT_TYPE=""),
        awy_segment(
            POINT_SEQ="30", FROM_POINT="BOSOX", FROM_PT_TYPE="RP", STATE_CODE="MA"
        ),
    ]

    _, points, unresolved = build.build_airways(
        [awy_base()], segments, [CRG_NAVAID], [BOSOX_FIX]
    )

    assert unresolved == 1
    assert len(points) == 3
    assert points[1][3] == "NOSUCH"
    assert points[1][5] is None
    assert points[1][6] is None


def test_a_navaid_typed_point_prefers_the_navaid_of_the_same_name() -> None:
    """Some names exist as both a navaid and a fix, in different places."""
    decoy_fix = ("CRG", 44.0, -93.0, "RP", "ZMP", "ZMP", "MN", "nasr")

    _, points, _ = build.build_airways(
        [awy_base()], [awy_segment()], [CRG_NAVAID], [decoy_fix]
    )

    assert points[0][5] == 30.338879


def test_a_duplicated_fix_name_is_disambiguated_by_state() -> None:
    fixes = [
        ("TWINS", 44.0, -93.0, "RP", "ZMP", "ZMP", "MN", "nasr"),
        ("TWINS", 30.0, -95.0, "RP", "ZHU", "ZHU", "TX", "nasr"),
    ]
    segment = awy_segment(FROM_POINT="TWINS", FROM_PT_TYPE="RP", STATE_CODE="TX")

    _, points, _ = build.build_airways([awy_base()], [segment], [], fixes)

    assert points[0][5] == 30.0


def test_airways_without_segments_are_not_carried_into_the_database() -> None:
    airways, points, _ = build.build_airways(
        [awy_base(), awy_base(AWY_ID="V999")], [awy_segment()], [CRG_NAVAID], []
    )

    assert [airway[0] for airway in airways] == ["V1"]
    assert len(points) == 1


def test_the_same_identifier_in_two_regions_stays_two_airways() -> None:
    segments = [
        awy_segment(),
        awy_segment(
            AWY_LOCATION="A",
            FROM_POINT="BOSOX",
            FROM_PT_TYPE="RP",
            STATE_CODE="MA",
        ),
    ]

    airways, _, _ = build.build_airways(
        [awy_base(), awy_base(AWY_LOCATION="A")],
        segments,
        [CRG_NAVAID],
        [BOSOX_FIX],
    )

    assert [(airway[0], airway[1]) for airway in airways] == [
        ("V1", "A"),
        ("V1", "C"),
    ]


def arb_segment(**overrides) -> dict[str, str]:
    row = {
        "LOCATION_ID": "ZAB",
        "LOCATION_NAME": "ALBUQUERQUE",
        "TYPE": "ARTCC",
        "ALTITUDE": "HIGH",
        "POINT_SEQ": "10",
        "LAT_DECIMAL": "35.766667",
        "LONG_DECIMAL": "-111.841667",
        "BNDRY_PT_DESCRIP": "",
    }
    row.update(overrides)
    return row


def test_boundary_rings_are_grouped_and_ordered() -> None:
    segments = [
        arb_segment(POINT_SEQ="30", LAT_DECIMAL="31.5", LONG_DECIMAL="-103.0"),
        arb_segment(POINT_SEQ="10"),
        arb_segment(POINT_SEQ="20", LAT_DECIMAL="35.7", LONG_DECIMAL="-110.233333"),
    ]

    boundaries, points = build.build_boundaries(segments)

    assert [point[3] for point in points] == [10, 20, 30]
    assert boundaries == [("ZAB", "ALBUQUERQUE", "ARTCC", "HIGH", 3, "nasr")]


def test_altitude_strata_are_separate_boundaries() -> None:
    """One centre publishes distinct low, high and unlimited rings."""
    segments = [arb_segment(ALTITUDE="HIGH"), arb_segment(ALTITUDE="LOW")]

    boundaries, _ = build.build_boundaries(segments)

    assert [boundary[3] for boundary in boundaries] == ["HIGH", "LOW"]


def test_fir_rings_are_kept_alongside_artcc_rings() -> None:
    segments = [
        arb_segment(),
        arb_segment(LOCATION_ID="ZAK", TYPE="FIR", ALTITUDE="UNLIMITED"),
    ]

    boundaries, _ = build.build_boundaries(segments)

    assert {boundary[2] for boundary in boundaries} == {"ARTCC", "FIR"}


# --- Output ---------------------------------------------------------------


def test_write_database_is_queryable_and_carries_metadata(tmp_path) -> None:
    database = tmp_path / "navigation.sqlite3"
    build.write_database(
        database,
        build.build_airports([ourairports_row()], [nasr_row()]),
        build.build_navaids([]),
        build.build_fixes([]),
        [],
        [],
        [],
        [],
        {"airac_cycle": "2026-07-09", "schema_version": "2", "sources": "test"},
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
        [],
        [],
        [],
        [],
    )
    metadata = {"airac_cycle": "2026-07-09", "schema_version": "2", "sources": "test"}

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
        [],
        [],
        [],
        [],
        {"airac_cycle": "2026-07-09", "schema_version": "2", "sources": "test"},
    )

    manifest = build.write_manifest(
        manifest_path,
        database,
        {
            "airac_cycle": "2026-07-09",
            "airport_count": "2",
            "navaid_count": "0",
            "fix_count": "0",
            "airway_count": "0",
            "airway_point_count": "0",
            "boundary_count": "0",
            "boundary_point_count": "0",
            "sources": "test",
        },
    )

    assert manifest["airac_cycle"] == "2026-07-09"
    assert manifest["database"]["sha256"] == build.sha256_of(database)
    assert manifest["database"]["size_bytes"] == database.stat().st_size
    assert manifest["counts"]["airports"] == 2
    assert manifest_path.exists()
