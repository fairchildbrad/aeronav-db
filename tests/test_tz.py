"""Time zone rules: resolution order, refusals, placement inputs."""

from __future__ import annotations

import pytest

from aeronav_db import tz

TAB = (
    "# test\n"
    "US\t+404251-0740023\tAmerica/New_York\tEastern (most areas)\n"
    "US\t+415100-0873900\tAmerica/Chicago\tCentral (most areas)\n"
    "US\t+394421-1045903\tAmerica/Denver\tMountain (most areas)\n"
    "DE,DK\t+5230+01322\tEurope/Berlin\tmost of Germany\n"
    "MX\t+1924-09909\tAmerica/Mexico_City\tCentral Mexico\n"
    "MX\t+2313-10625\tAmerica/Mazatlan\t"
    "Baja California Sur, Nayarit (most areas), Sinaloa\n"
    "MX\t+2048-10515\tAmerica/Bahia_Banderas\tBahía de Banderas\n"
    "DE\t+4742+00841\tEurope/Busingen\tBusingen\n"
    "FR,MC\t+4852+00220\tEurope/Paris\n"
    "PR,AG\t+182806-0660622\tAmerica/Puerto_Rico\n"
)


PARTIAL = (
    "DE,DE-BW,Europe/Berlin Europe/Busingen,most of Germany; Busingen\n"
    "MX,MX-NAY,America/Mazatlan America/Bahia_Banderas,Nayarit (most areas)\n"
)


def make(tmp_path, rules, overrides="", partial=PARTIAL):
    (tmp_path / "zone1970.tab").write_text(TAB)
    (tmp_path / "partial_regions.csv").write_text(
        "iso_country,region,zones,tzdata_quote\n" + partial)
    (tmp_path / "rules.csv").write_text("iso_country,region,county,tz,note\n" + rules)
    (tmp_path / "overrides.csv").write_text("airport_id,tz,source\n" + overrides)
    return tz.Rules.load(tmp_path)


GOOD = (
    "FR,*,*,Europe/Paris,single-zone country (zone1970.tab)\n"
    "PR,*,*,America/Puerto_Rico,single-zone country (zone1970.tab)\n"
    "US,US-NY,*,America/New_York,cited\n"
    "US,US-TX,*,SPLIT,split\n"
    "US,US-TX,EL PASO,America/Denver,cited\n"
    "US,US-TX,HARRIS,America/Chicago,cited\n"
)


def test_most_specific_rule_wins(tmp_path):
    rules = make(tmp_path, GOOD, "AP0000009,America/Chicago,Chart Supplement p.1\n")
    assert rules.resolve("AP1", "US", "US-TX", "EL PASO") == (
        "America/Denver", "county", None)
    assert rules.resolve("AP1", "US", "US-NY", "KINGS") == (
        "America/New_York", "region", None)
    assert rules.resolve("AP1", "FR", None, None) == ("Europe/Paris", "country", None)
    assert rules.resolve("ap0000009", "US", "US-NY", None) == (
        "America/Chicago", "override", None)


def test_unplaced_reasons(tmp_path):
    rules = make(tmp_path, GOOD)
    assert rules.resolve("A", "US", "US-TX", "CULBERSON")[2] == "no_county_match"
    assert rules.resolve("A", "US", None, None)[2] == "no_region"
    assert rules.resolve("A", "US", "US-OK", None)[2] == "multi_zone_country"
    assert rules.resolve("A", "XX", None, None)[2] == "no_rule"
    assert rules.resolve("A", "US", "US-OK", None)[:2] == (None, None)


@pytest.mark.parametrize("bad, message", [
    ("US,*,*,America/New_York,x\n", "country-wide rule would guess"),
    ("US,US-NY,*,Europe/Paris,x\n", "is not a US zone"),
    ("US,US-NY,*,America/New_York,\n", "cites a source"),
    ("US,US-NY,*,America/New_York,x\nUS,US-NY,*,America/Chicago,x\n", "conflicting"),
    ("US,US-NY,*,America/New_York,x\nUS,US-NY,KINGS,America/New_York,x\n",
     "mark the region SPLIT"),
    ("DE,DE-BW,*,Europe/Berlin,x\n", "split between zones"),
    ("MX,MX-NAY,*,America/Mazatlan,x\n", "split between zones"),
    ("ZZ,*,*,Europe/Paris,x\n", "not in zone1970.tab"),
])
def test_refusals(tmp_path, bad, message):
    with pytest.raises(tz.TzRulesError, match=message):
        make(tmp_path, bad)


def test_an_override_must_cite_its_source(tmp_path):
    with pytest.raises(tz.TzRulesError, match="no source"):
        make(tmp_path, GOOD, "AP0000009,America/Chicago,\n")


def test_placement_inputs():
    nasr = {"COUNTRY_CODE": "US", "STATE_CODE": "TX", "COUNTY_NAME": "El Paso"}
    assert tz.placement_inputs(nasr, None) == ("US", "US-TX", "EL PASO")
    pr = {"COUNTRY_CODE": "US", "STATE_CODE": "PR", "COUNTY_NAME": "X"}
    assert tz.placement_inputs(pr, None) == ("PR", None, None)
    oa = {"iso_country": "AU", "iso_region": "AU-NSW", "municipality": " Sydney "}
    assert tz.placement_inputs(None, oa) == ("AU", "AU-NSW", "SYDNEY")
    us_oa = {"iso_country": "US", "iso_region": "US-TX", "municipality": "El Paso"}
    assert tz.placement_inputs(None, us_oa) == ("US", "US-TX", None)
    assert tz.placement_inputs(nasr, oa)[0] == "US"
    ca = {"COUNTRY_CODE": "CA", "STATE_CODE": "BC", "COUNTY_NAME": ""}
    ca_oa = {"iso_country": "CA", "iso_region": "CA-BC", "municipality": "Abbotsford"}
    assert tz.placement_inputs(ca, ca_oa) == ("CA", "CA-BC", "ABBOTSFORD")
    assert tz.placement_inputs(ca, None) == ("CA", None, None)
    assert tz.placement_inputs(ca, oa) == ("CA", None, None)  # countries disagree


def test_the_committed_rules_load_and_tzdata_is_pinned():
    rules = tz.Rules.load()
    assert tz.tzdata_version() == "2026f"
    assert rules.resolve("A", "US", "US-AZ", "NAVAJO")[2] == "no_county_match"
    assert rules.resolve("A", "US", "US-AZ", "MARICOPA")[0] == "America/Phoenix"


def test_a_cited_conflict_leaves_the_airport_unplaced(tmp_path):
    rules = make(tmp_path, GOOD, "AP0000007,,source_conflict: CS prints UTC-6\n")
    assert rules.resolve("AP0000007", "US", "US-NY", None) == (
        None, None, "source_conflict")


def test_the_guard_is_per_region_not_per_zone(tmp_path):
    # Mazatlan's comment says "most" only of Nayarit; Sinaloa and BCS are whole.
    rules = make(tmp_path, GOOD + "MX,MX-SIN,*,America/Mazatlan,DOF 2022 art. 3\n"
                 "MX,MX-NAY,*,SPLIT,DOF 2022 art. 3\n"
                 "MX,MX-NAY,TEPIC,America/Mazatlan,DOF 2022 art. 3\n")
    assert rules.resolve("A", "MX", "MX-SIN", "MAZATLAN") == (
        "America/Mazatlan", "region", None)
    assert rules.resolve("A", "MX", "MX-NAY", "TEPIC")[1] == "county"
    assert rules.resolve("A", "MX", "MX-NAY", "BUCERIAS")[2] == "no_county_match"


@pytest.mark.parametrize("partial, message", [
    ("DE,DE-BW,Europe/Berlin Europe/Busingen,q\n", "Nayarit"),  # MX-NAY unlisted
    (PARTIAL + "MX,MX-SIN,America/Mazatlan,q\n", "two or more"),
    (PARTIAL + "MX,MX-SIN,America/Mazatlan America/Mexico_City,\n", "quote"),
    (PARTIAL + "MX,SIN,America/Mazatlan America/Mexico_City,q\n", "ISO 3166-2"),
])
def test_partial_list_is_complete_and_well_formed(tmp_path, partial, message):
    with pytest.raises(tz.TzRulesError, match=message):
        make(tmp_path, GOOD, partial=partial)


def test_a_country_level_qualifier_is_exempted_with_a_quote(tmp_path):
    partial = PARTIAL.replace("DE,DE-BW,Europe/Berlin Europe/Busingen,",
                              "DE,DE-*,Europe/Berlin,")
    make(tmp_path, GOOD, partial=partial)


def test_gate(tmp_path):
    import sqlite3
    db = tmp_path / "n.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE airport_identity (airport_id, ourairports_id, "
                 "iso_country, tz, tz_unplaced, in_current_cycle)")
    conn.executemany("INSERT INTO airport_identity VALUES (?,?,?,?,?,1)", [
        ("AP1", 1, "MX", "America/Cancun", None),
        ("AP2", 2, "MX", None, "no_county_match"),     # scheduled, unplaced
        ("AP3", 3, "MX", None, "no_county_match"),     # not scheduled
        ("AP4", 4, "AQ", None, "multi_zone_country"),  # by design
    ])
    conn.commit()
    conn.close()
    oa = tmp_path / "oa.csv"
    oa.write_text("id,scheduled_service\n1,yes\n2,yes\n3,no\n4,yes\n")
    (tmp_path / "unplaced_by_design.csv").write_text("airport_id,reason\n")
    passed, lines = tz.gate(str(db), str(oa), tmp_path)
    assert not passed and any("MX has 1 scheduled" in line for line in lines)
    (tmp_path / "unplaced_by_design.csv").write_text(
        "airport_id,reason\nAP2,no official source places it; searched DOF\n")
    assert tz.gate(str(db), str(oa), tmp_path)[0]
