"""The chained build: cycle N carries airport identity forward from N-1's file.

Small synthetic source files, run through build() end to end. No network.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import zipfile

import pytest

from aeronav_db import build
from aeronav_db.identity import load_state
from aeronav_db.verify import verify_chain

C1, C2, C3 = "2026-07-09", "2026-08-06", "2026-09-03"

NASR_FIELDS = [
    "SITE_NO", "SITE_TYPE_CODE", "ARPT_ID", "ICAO_ID", "ARPT_NAME", "ARPT_STATUS",
    "LAT_DECIMAL", "LONG_DECIMAL", "COUNTRY_CODE",
]
OA_FIELDS = [
    "id", "ident", "type", "name", "latitude_deg", "longitude_deg",
    "iso_country", "icao_code", "iata_code",
]


def nasr(site, faa, icao="", lat="35.0", lon="-80.0", status="O", country="US",
         site_type="A"):
    return dict(zip(NASR_FIELDS, [site, site_type, faa, icao, f"FIELD {faa}",
                                  status, lat, lon, country], strict=True))


def oa(oa_id, ident, iata="", icao="", lat="51.5", lon="-0.5", country="GB",
       kind="large_airport"):
    return dict(zip(OA_FIELDS, [oa_id, ident, kind, f"OA {ident}", lat, lon,
                                country, icao, iata], strict=True))


def _csv(fields, rows) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def write_sources(directory, name, nasr_rows, oa_rows):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as archive:
        archive.writestr("APT_BASE.csv", _csv(NASR_FIELDS, nasr_rows))
        for table in build.NASR_TABLES[1:]:
            archive.writestr(table, b"X\n")
    outer_path = directory / f"{name}.zip"
    with zipfile.ZipFile(outer_path, "w") as archive:
        archive.writestr("CSV_Data/csv.zip", inner.getvalue())
    oa_path = directory / f"{name}-airports.csv"
    oa_path.write_bytes(_csv(OA_FIELDS, oa_rows))
    navaids_path = directory / f"{name}-navaids.csv"
    navaids_path.write_bytes(b"ident\n")
    return outer_path, oa_path, navaids_path


def run_build(tmp_path, cycle, nasr_rows, oa_rows, output, **kwargs):
    nasr_zip, oa_csv, navaids_csv = write_sources(
        tmp_path, cycle, nasr_rows, oa_rows
    )
    return build.build(
        cycle=cycle,
        nasr_zip_path=str(nasr_zip),
        ourairports_csv_path=str(oa_csv),
        ourairports_navaids_csv_path=str(navaids_csv),
        output=output,
        manifest=output.with_suffix(".json"),
        **kwargs,
    )


def ids(path):
    connection = sqlite3.connect(path)
    try:
        return dict(connection.execute("SELECT code, airport_id FROM airports"))
    finally:
        connection.close()


def metadata(path):
    connection = sqlite3.connect(path)
    try:
        return dict(connection.execute("SELECT key, value FROM metadata"))
    finally:
        connection.close()


CYCLE1 = ([nasr("06278.", "2Y1"), nasr("1.", "AAA", "KAAA", lat="36.0")],
          [oa("10", "EGLL", iata="LHR", icao="EGLL")])
CYCLE2 = ([nasr("06278.", "47IA"), nasr("1.", "AAA", "KAAA", lat="36.0")],
          [oa("10", "EGLL", iata="LHR", icao="EGLL")])


def test_a_rename_keeps_its_id_across_two_files(tmp_path):
    first, second = tmp_path / "c1.sqlite3", tmp_path / "c2.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    run_build(tmp_path, C2, *CYCLE2, second, previous_db=first)

    assert ids(first)["2Y1"] == ids(second)["47IA"]
    assert ids(first)["LHR"] == ids(second)["LHR"] == ids(second)["EGLL"]
    assert verify_chain(second, first) == []
    meta = metadata(second)
    assert meta["schema_version"] == "3"
    assert meta["history_start"] == C1
    assert meta["previous_cycle"] == C1
    assert meta["previous_db_sha256"] == build.sha256_of(first)
    assert metadata(first)["previous_cycle"] == ""


def test_a_nasr_identifier_is_typed_faa(tmp_path):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    connection = sqlite3.connect(first)
    try:
        assert connection.execute(
            "SELECT code_type FROM airports WHERE code = 'AAA'"
        ).fetchone() == ("faa",)
    finally:
        connection.close()


def test_state_round_trips_through_the_file(tmp_path):
    first, second = tmp_path / "c1.sqlite3", tmp_path / "c2.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    run_build(tmp_path, C2, *CYCLE2, second, previous_db=first)
    connection = sqlite3.connect(second)
    try:
        state = load_state(connection)
    finally:
        connection.close()

    copy = tmp_path / "copy.sqlite3"
    build.write_database(copy, [], [], [], [], [], [], [],
                         {"airac_cycle": C2, "airport_id_next": str(state.next_id)},
                         state)
    connection = sqlite3.connect(copy)
    try:
        assert load_state(connection) == state
    finally:
        connection.close()


def test_same_inputs_give_identical_identity_tables(tmp_path):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    outputs = []
    for name in ("a", "b"):
        output = tmp_path / f"{name}.sqlite3"
        run_build(tmp_path, C2, *CYCLE2, output, previous_db=first)
        connection = sqlite3.connect(output)
        try:
            outputs.append([
                connection.execute(f"SELECT * FROM {table} ORDER BY 1, 2, 3").fetchall()  # noqa: S608
                for table in ("airport_identity", "airport_codes",
                              "airport_presence", "airport_aliases", "airports")
            ])
        finally:
            connection.close()
    assert outputs[0] == outputs[1]


def test_convergence_across_two_files_passes_verify_previous(tmp_path):
    """sqwkd A2: a merged id keeps its rows; verify --previous accepts it."""
    first, second = tmp_path / "c1.sqlite3", tmp_path / "c2.sqlite3"
    # The OurAirports row shares no code with the NASR field in cycle 1, so it
    # stands alone; in cycle 2 it carries the field's ICAO code and attaches.
    us_oa = oa("500", "XYZ", iata="XYZ", lat="36.0", lon="-80.0", country="US",
               kind="small_airport")
    run_build(tmp_path, C1, CYCLE1[0], CYCLE1[1] + [us_oa], first, bootstrap=True)
    attached = dict(us_oa, icao_code="KAAA")
    run_build(tmp_path, C2, CYCLE2[0], CYCLE2[1] + [attached], second,
              previous_db=first)

    assert verify_chain(second, first) == []
    connection = sqlite3.connect(second)
    try:
        alias = connection.execute(
            "SELECT alias_id, airport_id, effective_date FROM airport_aliases"
        ).fetchall()
        assert len(alias) == 1 and alias[0][2] == C2
        merged = alias[0][0]
        rows = connection.execute(
            "SELECT valid_to FROM airport_codes WHERE airport_id = ?", (merged,)
        ).fetchall()
        assert rows == [(C2,)]
        assert ids(second)["XYZ"] == alias[0][1]
    finally:
        connection.close()


# --- AC-8: refusals -------------------------------------------------------------


def test_no_previous_and_no_bootstrap_is_refused(tmp_path):
    with pytest.raises(build.BuildError, match="--bootstrap"):
        run_build(tmp_path, C1, *CYCLE1, tmp_path / "c1.sqlite3")


def test_bootstrap_with_previous_is_refused(tmp_path):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    with pytest.raises(build.BuildError, match="mutually exclusive"):
        run_build(tmp_path, C2, *CYCLE2, tmp_path / "c2.sqlite3",
                  previous_db=first, bootstrap=True)


def test_previous_equal_to_output_is_refused_and_left_intact(tmp_path):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    before = build.sha256_of(first)
    with pytest.raises(build.BuildError, match="overwrite"):
        run_build(tmp_path, C2, *CYCLE2, first, previous_db=first)
    assert build.sha256_of(first) == before


@pytest.mark.parametrize("cycle", [C1, "2026-06-11"])
def test_previous_not_older_than_the_cycle_is_refused(tmp_path, cycle):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    with pytest.raises(build.BuildError, match="must precede"):
        run_build(tmp_path, cycle, *CYCLE2, tmp_path / "c2.sqlite3",
                  previous_db=first)


def test_a_schema_2_previous_is_refused(tmp_path):
    first = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    connection = sqlite3.connect(first)
    connection.execute("UPDATE metadata SET value = '2' WHERE key = 'schema_version'")
    connection.commit()
    connection.close()
    with pytest.raises(build.BuildError, match="schema 2"):
        run_build(tmp_path, C2, *CYCLE2, tmp_path / "c2.sqlite3", previous_db=first)


def test_a_corrupted_previous_is_refused_and_no_output_is_written(tmp_path):
    first, second = tmp_path / "c1.sqlite3", tmp_path / "c2.sqlite3"
    run_build(tmp_path, C1, *CYCLE1, first, bootstrap=True)
    second.write_bytes(b"keep me")
    connection = sqlite3.connect(first)
    connection.execute("UPDATE metadata SET value = '1' WHERE key = 'airport_id_next'")
    connection.commit()
    connection.close()
    with pytest.raises(build.BuildError, match="airport_id_next"):
        run_build(tmp_path, C2, *CYCLE2, second, previous_db=first)
    assert second.read_bytes() == b"keep me"
    assert not second.with_name(second.name + ".partial").exists()


def test_a_failed_invariant_leaves_the_old_output_in_place(tmp_path):
    """Two NASR records claiming one ICAO code violate AC-6: the build fails,
    and the file already at the output path is untouched."""
    output = tmp_path / "c1.sqlite3"
    output.write_bytes(b"keep me")
    clash = [nasr("1.", "AAA", "KAAA"), nasr("2.", "BBB", "KAAA", lat="40.0")]
    with pytest.raises(build.BuildError, match="icao codes held by more than one"):
        run_build(tmp_path, C1, clash, [], output, bootstrap=True)
    assert output.read_bytes() == b"keep me"
    assert not output.with_name(output.name + ".partial").exists()


def test_an_unknown_nasr_status_is_never_guessed(tmp_path):
    with pytest.raises(ValueError, match="ARPT_STATUS"):
        run_build(tmp_path, C1, [nasr("1.", "AAA", status="X")], [],
                  tmp_path / "c1.sqlite3", bootstrap=True)


def test_closed_nasr_fields_get_an_identity_but_no_airports_row(tmp_path):
    output = tmp_path / "c1.sqlite3"
    run_build(tmp_path, C1, [nasr("1.", "AAA"), nasr("2.", "CCC", status="CP",
                                                      lat="40.0")], [],
              output, bootstrap=True)
    connection = sqlite3.connect(output)
    try:
        assert connection.execute(
            "SELECT source_status FROM airport_identity i JOIN airport_codes c "
            "USING (airport_id) WHERE c.code = 'CCC'"
        ).fetchone() == ("closed_permanently",)
    finally:
        connection.close()
    assert "CCC" not in ids(output)


def test_a_non_us_field_listed_by_both_sources_is_one_airport(tmp_path):
    """AC-6 gate: NASR lists some foreign fields (CA, BS, FM...). The
    OurAirports row for the same field attaches when the countries match."""
    output = tmp_path / "c1.sqlite3"
    run_build(
        tmp_path, C1,
        [nasr("50000.", "CYAM", "CYAM", lat="46.48", lon="-84.51", country="CA")],
        [oa("1657", "CYAM", iata="YAM", icao="CYAM", lat="46.485", lon="-84.509",
            country="CA", kind="medium_airport")],
        output, bootstrap=True,
    )
    assert ids(output)["YAM"] == ids(output)["CYAM"]
