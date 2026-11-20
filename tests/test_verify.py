"""The publish gate. Each test breaks a real build in one way and expects a
problem to be reported -- a gate that cannot fail is not a gate.
"""

import sqlite3

import pytest

from aeronav_db.build import IDENTITY_SCHEMA
from aeronav_db.identity import IdentityState, Observation, apply_cycle, dump_state
from aeronav_db.verify import verify_database

CYCLE = "2026-07-09"


def observation(source, key, codes, lat, lon, country="US"):
    nasr = source == "nasr"
    return Observation(
        source=source, nasr_site_no=key if nasr else None,
        nasr_site_type="A" if nasr else None,
        ourairports_id=None if nasr else key, codes=tuple(codes), lat=lat,
        lon=lon, name=key, kind="airport", source_status="operational",
        iso_country=country,
    )


# Minted in NASR site order: AP0000001 is the DJT canary (NASR and OurAirports
# records of one field, formerly PBI); AP0000002 stands for every filler airport.
IDENTITY_OBSERVATIONS = [
    observation("nasr", "1.", [("faa", "FILL")], 40.0, -100.0),
    observation("nasr", "03555.", [("faa", "DJT"), ("icao", "KDJT")], 26.68, -80.1),
    observation("ourairports", "3766", [("iata", "DJT"), ("icao", "KDJT")],
                26.68, -80.1),
]


def identity_metadata(state):
    return {
        "airport_id_next": str(state.next_id),
        "history_start": CYCLE,
        "previous_cycle": "",
        "previous_db_sha256": "",
    }

GOOD_AIRPORTS = [
    ("DFW", 32.897233, -97.037695, "DALLAS-FORT WORTH INTL", "airport", "iata", "nasr"),
    ("KDFW", 32.897233, -97.037695, "DFW INTL", "airport", "icao", "nasr"),
    ("DEN", 39.861667, -104.673167, "DENVER INTL", "airport", "iata", "nasr"),
    ("ANC", 61.174085, -149.998138, "TED STEVENS", "airport", "iata", "nasr"),
    ("LHR", 51.470748, -0.459909, "Heathrow", "large_airport", "iata", "ourairports"),
    ("EGLL", 51.470748, -0.459909, "Heathrow", "large_airport", "icao", "ourairports"),
    ("SYD", -33.946098, 151.177002, "Sydney", "large_airport", "iata", "ourairports"),
    # Foreign IATA codes that collide with a US FAA local identifier -- the
    # class of bug that put Punta Cana in Georgia and Dublin in Pennsylvania.
    ("PUJ", 18.567093, -68.364558, "Punta Cana", "large_airport", "iata",
     "ourairports"),
    ("DUB", 53.421333, -6.270075, "Dublin", "large_airport", "iata", "ourairports"),
    ("CPT", -33.96480, 18.601700, "Cape Town", "large_airport", "iata", "ourairports"),
    ("AUH", 24.433001, 54.651100, "Zayed Intl", "large_airport", "iata", "ourairports"),
]


# The canary navaids the gate looks for, one per source layer. `BIG` is here
# twice on purpose: the same identifier in Alaska and outside London, which is
# the case a position-based consumer has to survive.
GOOD_NAVAIDS = [
    ("CRG", "VORTAC", "CRAIG", 30.338879, -81.513611, "114.5", "nasr"),
    ("BIG", "VORTAC", "BIG DELTA", 64.0044, -145.716, "114.9", "nasr"),
    ("BIG", "VOR/DME", "Biggin", 51.3308, 0.034811, "115.1", "ourairports"),
    ("LAM", "VOR/DME", "Lambourne", 51.646, 0.151666, "115.6", "ourairports"),
    ("NTM", "VOR/DME", "Nattenheim", 50.0158, 6.531789, "115.3", "ourairports"),
]


# The canary airway and boundary the gate looks for, with enough real geometry
# to satisfy it. V1 starts at the Craig VORTAC; ZAB is Albuquerque Center.
GOOD_AIRWAY_POINTS = [
    ("V1", "C", 10, "CRG", "VORTAC", 30.338879, -81.509927, "ZJX", "FL"),
    ("V1", "C", 20, "LLIPS", "RP", 30.666936, -81.371744, "ZJX", "FL"),
    ("V1", "C", 30, "OCNOP", "RP", 30.862219, -81.289061, "ZJX", "FL"),
]
GOOD_BOUNDARY_POINTS = [
    ("ZAB", "ARTCC", "HIGH", 10, 35.766667, -111.841667, None),
    ("ZAB", "ARTCC", "HIGH", 20, 35.7, -110.233333, None),
    ("ZAB", "ARTCC", "HIGH", 30, 31.5, -103.0, None),
    ("ZAK", "FIR", "UNLIMITED", 10, 40.0, -140.0, None),
    ("ZAK", "FIR", "UNLIMITED", 20, 30.0, -140.0, None),
    ("ZAK", "FIR", "UNLIMITED", 30, 30.0, -150.0, None),
]


def build_database(
    path,
    *,
    airports=None,
    nasr_filler=13_000,
    ourairports_filler=13_000,
    navaids=1_200,
    ourairports_navaids=6_000,
    canary_navaids=None,
    fixes=60_000,
    airways=1_100,
    airway_points=None,
    unplaced_airway_points=0,
    boundaries=None,
    boundary_points=None,
    metadata=None,
    size_padding=1_200_000,
    identity_state=None,
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
        CREATE TABLE airways (awy_id TEXT, location TEXT, designation TEXT,
            regulatory TEXT, point_count INTEGER, source TEXT);
        CREATE TABLE airway_points (awy_id TEXT, location TEXT, seq INTEGER,
            point_id TEXT, point_type TEXT, lat REAL, lon REAL, artcc TEXT,
            state_code TEXT);
        CREATE TABLE boundaries (boundary_id TEXT, name TEXT, kind TEXT,
            altitude TEXT, point_count INTEGER, source TEXT);
        CREATE TABLE boundary_points (boundary_id TEXT, kind TEXT,
            altitude TEXT, seq INTEGER, lat REAL, lon REAL, description TEXT);
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
         for i in range(navaids)]
        + [(f"W{i}", "VOR/DME", "filler", 50.0, 10.0, "112.3", "ourairports")
           for i in range(ourairports_navaids)]
        + (GOOD_NAVAIDS if canary_navaids is None else canary_navaids),
    )
    connection.executemany(
        "INSERT INTO fixes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(f"FIX{i:05d}", 40.0, -100.0, "RP", "ZNY", "ZNY", "NY", "nasr")
         for i in range(fixes)],
    )
    points = (
        GOOD_AIRWAY_POINTS if airway_points is None else airway_points
    ) + [
        # Filler segments on their own airways, so the point-count floor is met
        # without the canary airway growing an implausible number of points.
        (f"J{i}", "C", seq, f"PT{i:05d}_{seq}", "RP", 40.0, -100.0, "ZNY", "NY")
        for i in range(max(0, airways - 1))
        for seq in range(10, 160, 10)
    ] + [
        ("UNPLACED", "C", seq, f"GAP{seq}", None, None, None, None, None)
        for seq in range(unplaced_airway_points)
    ]
    connection.executemany(
        "INSERT INTO airway_points VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", points
    )
    # Every point must belong to a declared airway or the gate reports orphans.
    declared = {(row[0], row[1]) for row in points}
    connection.executemany(
        "INSERT INTO airways VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                awy_id,
                location,
                "V",
                "N",
                sum(1 for row in points if (row[0], row[1]) == (awy_id, location)),
                "nasr",
            )
            for awy_id, location in sorted(declared)
        ],
    )

    rings = GOOD_BOUNDARY_POINTS if boundary_points is None else boundary_points
    rings = rings + [
        (f"Z{i:02d}", "ARTCC", "LOW", seq, 40.0, -100.0, None)
        for i in range(40)
        for seq in range(10, 610, 10)
    ]
    connection.executemany(
        "INSERT INTO boundary_points VALUES (?, ?, ?, ?, ?, ?, ?)", rings
    )
    ring_keys = {(row[0], row[1], row[2]) for row in rings}
    connection.executemany(
        "INSERT INTO boundaries VALUES (?, ?, ?, ?, ?, ?)",
        boundaries
        if boundaries is not None
        else [
            (
                boundary_id,
                "filler",
                kind,
                altitude,
                sum(1 for row in rings if (row[0], row[1], row[2]) == key),
                "nasr",
            )
            for key in sorted(ring_keys)
            for boundary_id, kind, altitude in (key,)
        ],
    )

    state = identity_state or apply_cycle(
        IdentityState.empty(), CYCLE, IDENTITY_OBSERVATIONS
    )
    connection.executescript(IDENTITY_SCHEMA)
    connection.execute("ALTER TABLE airports ADD COLUMN airport_id TEXT")
    connection.execute("UPDATE airports SET airport_id = 'AP0000002'")
    dump_state(connection, state)
    connection.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        (metadata or {
            "airac_cycle": state.last_cycle,
            "schema_version": "3",
            "sources": "FAA NASR; OurAirports",
            "licence": "Public domain.",
            "disclaimer": "NOT FOR NAVIGATION.",
            **identity_metadata(state),
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
        ourairports_navaids=0,
        canary_navaids=[],
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
        ({"airways": 2}, "airway_points"),
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


def test_airway_points_that_mostly_fail_to_resolve_are_reported(tmp_path) -> None:
    """The failure mode unique to airways.

    Airway points carry names, not coordinates, so a NASR column rename leaves
    every table full and correctly shaped while the geometry is entirely
    absent. Row counts cannot see it; this is the check that can.
    """
    database = build_database(
        tmp_path / "navigation.sqlite3", unplaced_airway_points=10_000
    )

    assert any(
        "without coordinates" in problem for problem in verify_database(database)
    )


def test_airway_points_belonging_to_no_airway_are_reported(tmp_path) -> None:
    database = build_database(
        tmp_path / "navigation.sqlite3",
        airway_points=GOOD_AIRWAY_POINTS
        + [("GHOST", "C", 10, "NOWHR", "RP", 40.0, -100.0, "ZNY", "NY")],
    )
    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM airways WHERE awy_id = 'GHOST'")
    connection.commit()
    connection.close()

    assert any(
        "belonging to no airway" in problem for problem in verify_database(database)
    )


def test_a_canary_airway_starting_in_the_wrong_place_is_reported(tmp_path) -> None:
    """V1 rerouted from Florida into Kansas -- a plausible-looking mis-resolve."""
    moved = [(*GOOD_AIRWAY_POINTS[0][:5], 38.0, -98.0, "ZKC", "KS")]
    database = build_database(
        tmp_path / "navigation.sqlite3",
        airway_points=moved + list(GOOD_AIRWAY_POINTS[1:]),
    )

    assert any("canary airway" in problem for problem in verify_database(database))


def test_losing_the_fir_boundaries_is_reported(tmp_path) -> None:
    """ARTCC rings alone would still meet every row-count floor."""
    artcc_only = [row for row in GOOD_BOUNDARY_POINTS if row[1] != "FIR"]
    database = build_database(
        tmp_path / "navigation.sqlite3", boundary_points=artcc_only
    )

    assert any("no FIR boundaries" in problem for problem in verify_database(database))


def test_a_boundary_ring_too_small_to_enclose_anything_is_reported(
    tmp_path,
) -> None:
    database = build_database(tmp_path / "navigation.sqlite3")
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE boundaries SET point_count = 2 WHERE boundary_id = 'ZAB'"
    )
    connection.commit()
    connection.close()

    assert any(
        "fewer than three points" in problem for problem in verify_database(database)
    )


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


def test_a_database_without_the_terms_is_rejected(tmp_path) -> None:
    """The .sqlite3 is fetched on its own, so it is the only place most
    consumers will ever see the licence or the not-for-navigation warning.
    A build that stopped writing them must not reach a release."""
    path = build_database(
        tmp_path / "no_terms.sqlite3",
        metadata={
            "airac_cycle": "2026-08-06",
            "schema_version": "2",
            "sources": "FAA NASR; OurAirports",
        },
    )
    problems = verify_database(path)
    assert any("licence" in p for p in problems)
    assert any("disclaimer" in p for p in problems)


def test_missing_metadata_is_reported(tmp_path) -> None:
    database = build_database(
        tmp_path / "navigation.sqlite3",
        metadata={"schema_version": "1", "sources": "test"},
    )

    assert any("airac_cycle" in problem for problem in verify_database(database))


# --- Schema 3: identity guarantees (AC-4, AC-6, AC-7, AC-9) ---------------------

from aeronav_db.verify import check_chain, check_identity  # noqa: E402

C2 = "2026-08-06"


def identity_db(state, previous_cycle="", previous_sha="", airports=()):
    """An in-memory file holding just what the identity checks read."""
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);"
        "CREATE TABLE airports (code TEXT, airport_id TEXT);" + IDENTITY_SCHEMA
    )
    dump_state(connection, state)
    connection.executemany("INSERT INTO airports VALUES (?, ?)", airports)
    meta = identity_metadata(state) | {
        "airac_cycle": state.last_cycle,
        "previous_cycle": previous_cycle,
        "previous_db_sha256": previous_sha,
    }
    connection.executemany("INSERT INTO metadata VALUES (?, ?)", meta.items())
    return connection


def first_state():
    return apply_cycle(IdentityState.empty(), CYCLE, IDENTITY_OBSERVATIONS)


def second_state(observations=None):
    return apply_cycle(first_state(), C2, observations or IDENTITY_OBSERVATIONS)


def problems_after(sql, *args, state=None):
    connection = identity_db(state or first_state())
    connection.execute(sql, args)
    return check_identity(connection)[0]


def test_identity_invariants_hold_on_a_clean_state():
    problems, notes = check_identity(identity_db(first_state(),
                                                 airports=[("DJT", "AP0000001")]))
    assert problems == []
    assert notes == ["IATA codes held by more than one present airport: 0"]


def test_an_id_outside_the_ap7_shape_is_reported():
    # CHECK stops a bad airport_identity id at insert; an alias has no CHECK.
    problems = problems_after(
        "INSERT INTO airport_aliases VALUES ('AP12', 'AP0000001', ?, 'converged')",
        CYCLE,
    )
    assert any("AP+7" in p for p in problems)


def test_a_two_hop_alias_is_reported():
    connection = identity_db(first_state())
    connection.executescript(
        "INSERT INTO airport_aliases VALUES "
        "('AP0000003', 'AP0000002', '2026-07-09', 'converged'),"
        "('AP0000002', 'AP0000001', '2026-07-09', 'converged');"
    )
    assert any("one hop" in p for p in check_identity(connection)[0])


def test_an_airports_row_without_an_identity_is_reported():
    connection = identity_db(first_state(), airports=[("ZZZ", "AP0000099")])
    assert any("airports: 1 rows name no" in p for p in check_identity(connection)[0])


def test_an_orphan_code_row_is_reported():
    problems = problems_after(
        "INSERT INTO airport_codes VALUES ('AP0000077', 'faa', 'ZZZ', 'nasr', ?, NULL)",
        CYCLE,
    )
    assert any("airport_codes: 1 rows name no" in p for p in problems)


def test_a_counter_at_or_below_the_highest_id_is_reported():
    problems = problems_after(
        "UPDATE metadata SET value = '2' WHERE key = 'airport_id_next'"
    )
    assert any("airport_id_next 2" in p for p in problems)


def test_in_current_cycle_disagreeing_with_presence_is_reported():
    problems = problems_after("UPDATE airport_identity SET in_current_cycle = 0")
    assert any("in_current_cycle" in p for p in problems)


def test_an_faa_code_with_two_current_holders_is_reported():
    problems = problems_after(
        "INSERT INTO airport_codes VALUES ('AP0000002', 'faa', 'DJT', 'nasr', ?, NULL)",
        CYCLE,
    )
    assert any("faa codes held by more than one airport now" in p for p in problems)
    assert any("faa codes have overlapping intervals" in p for p in problems)


def test_overlapping_closed_icao_intervals_are_reported():
    problems = problems_after(
        "INSERT INTO airport_codes VALUES "
        "('AP0000002', 'icao', 'KDJT', 'nasr', '2026-06-11', ?)",
        C2,
        state=second_state(),
    )
    assert any("icao codes have overlapping intervals" in p for p in problems)


def test_shared_iata_codes_are_counted_not_failed():
    foreign = observation("ourairports", "99", [("iata", "DJT")], 10.0, 10.0, "XX")
    state = apply_cycle(IdentityState.empty(), CYCLE, [*IDENTITY_OBSERVATIONS, foreign])
    problems, notes = check_identity(identity_db(state))
    assert problems == []
    assert notes == ["IATA codes held by more than one present airport: 1"]


def test_a_skipped_cycle_warns_but_does_not_fail():
    later = apply_cycle(first_state(), "2026-09-03", IDENTITY_OBSERVATIONS)
    problems, notes = check_identity(identity_db(later, previous_cycle=CYCLE))
    assert problems == []
    assert any("56 days" in n for n in notes)


def test_the_djt_canary_is_part_of_the_publish_gate(tmp_path):
    # The OurAirports row fails to attach (wrong country), so IATA DJT and
    # ICAO KDJT name two different ids: exactly the regression the canary is for.
    split = [IDENTITY_OBSERVATIONS[0],
             observation("nasr", "03555.", [("faa", "DJT"), ("icao", "KDJT")],
                         26.68, -80.1),
             observation("ourairports", "3766", [("iata", "DJT")], 26.68, -80.1,
                         "XX")]
    state = apply_cycle(IdentityState.empty(), CYCLE, split)
    database = build_database(tmp_path / "navigation.sqlite3", identity_state=state)
    assert any("canary identity" in p for p in verify_database(database))


# --- verify --previous ---------------------------------------------------------


def chain(mutate_sql=None, *args, new_state=None):
    old = identity_db(first_state())
    new = identity_db(new_state or second_state(), previous_cycle=CYCLE,
                      previous_sha="abc")
    if mutate_sql:
        new.execute(mutate_sql, args)
    return check_chain(new, old, "abc")


def test_a_clean_chain_passes():
    assert chain() == []


def test_a_missing_previous_id_is_reported():
    problems = chain("DELETE FROM airport_identity WHERE airport_id = 'AP0000001'")
    assert any("previous airport ids are missing" in p for p in problems)


def test_a_changed_closed_interval_is_reported():
    gone = second_state([IDENTITY_OBSERVATIONS[0]])  # DJT absent: closes at C2
    third = apply_cycle(gone, "2026-09-03", [IDENTITY_OBSERVATIONS[0]])
    old = identity_db(gone)
    new = identity_db(third, previous_cycle=C2, previous_sha="abc")
    new.execute("UPDATE airport_codes SET valid_to = '2026-08-20' "
                "WHERE valid_to = ?", (C2,))
    problems = check_chain(new, old, "abc")
    assert any("closed intervals changed or vanished" in p for p in problems)


def test_an_open_interval_closed_at_the_wrong_date_is_reported():
    problems = chain(
        "UPDATE airport_codes SET valid_to = '2026-07-20' WHERE code = 'FILL'"
    )
    assert any("closed at 2026-07-20, not 2026-08-06" in p for p in problems)


def test_a_backdated_new_interval_is_reported():
    problems = chain(
        "INSERT INTO airport_codes VALUES "
        "('AP0000001', 'iata', 'FIL', 'ourairports', '2026-06-11', NULL)"
    )
    assert any("new intervals not dated" in p for p in problems)


def test_a_wrong_parent_checksum_is_reported():
    old = identity_db(first_state())
    new = identity_db(second_state(), previous_cycle=CYCLE, previous_sha="abc")
    assert any("previous_db_sha256" in p for p in check_chain(new, old, "def"))


def test_a_retired_nasr_country_code_is_refused():
    """01-03 AC-2: 'AN' fails the output check; successors, NULL, XK pass;
    check_identity (also run on input files) never reports it."""
    from aeronav_db.verify import check_retired_countries

    for country, refused in (("AN", True), ("BQ", False), ("SX", False),
                             (None, False), ("XK", False)):
        connection = identity_db(first_state())
        connection.execute("UPDATE airport_identity SET iso_country = ? "
                           "WHERE airport_id = 'AP0000001'", (country,))
        found = check_retired_countries(connection)
        assert any("retired NASR country" in p for p in found) is refused, country
        assert not any("retired" in p for p in check_identity(connection)[0])
