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
    "DE\t+4742+00841\tEurope/Busingen\tBusingen\n"
    "FR,MC\t+4852+00220\tEurope/Paris\n"
    "PR,AG\t+182806-0660622\tAmerica/Puerto_Rico\n"
)


def make(tmp_path, rules, overrides=""):
    (tmp_path / "zone1970.tab").write_text(TAB)
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
    ("DE,DE-BY,*,Europe/Berlin,x\n", "covers only part"),
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
    oa = {"iso_country": "AU", "iso_region": "AU-NSW"}
    assert tz.placement_inputs(None, oa) == ("AU", "AU-NSW", None)
    assert tz.placement_inputs(nasr, oa)[0] == "US"


def test_the_committed_rules_load_and_tzdata_is_pinned():
    rules = tz.Rules.load()
    assert tz.tzdata_version() == "2026f"
    assert rules.resolve("A", "US", "US-AZ", "NAVAJO")[2] == "no_county_match"
    assert rules.resolve("A", "US", "US-AZ", "MARICOPA")[0] == "America/Phoenix"


def test_a_cited_conflict_leaves_the_airport_unplaced(tmp_path):
    rules = make(tmp_path, GOOD, "AP0000007,,source_conflict: CS prints UTC-6\n")
    assert rules.resolve("AP0000007", "US", "US-NY", None) == (
        None, None, "source_conflict")
