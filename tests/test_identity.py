"""Identity engine: permanent airport ids and dated code history.

Fixtures mirror cases observed in real data: the 2026-07-09 vs 2026-10-29
NASR diff and a year of OurAirports history.
"""

from __future__ import annotations

import dataclasses
import re

import pytest

from aeronav_db.identity import (
    Alias,
    IdentityState,
    Observation,
    apply_cycle,
    lookup,
    normalize_id,
)

C1, C2, C3 = "2026-07-09", "2026-08-06", "2026-09-03"


def nasr(site, faa, icao=None, *, site_type="A", lat=35.0, lon=-80.0,
         status="operational"):
    codes = [("faa", faa)] + ([("icao", icao)] if icao else [])
    return Observation(
        source="nasr", nasr_site_no=site, nasr_site_type=site_type,
        ourairports_id=None, codes=tuple(codes), lat=lat, lon=lon,
        name=f"FIELD {faa}", kind="airport", source_status=status,
        iso_country="US",
    )


def oa(oa_id, *, iata=None, icao=None, country="US", lat=35.0, lon=-80.0,
       status="operational"):
    codes = ([("iata", iata)] if iata else []) + ([("icao", icao)] if icao else [])
    return Observation(
        source="ourairports", nasr_site_no=None, nasr_site_type=None,
        ourairports_id=oa_id, codes=tuple(codes), lat=lat, lon=lon,
        name=f"OA {oa_id}", kind="small_airport", source_status=status,
        iso_country=country,
    )


def run(*cycles):
    state = IdentityState.empty()
    states = []
    for date, observations in cycles:
        state = apply_cycle(state, date, observations)
        states.append(state)
    return states


def only_id(state, scheme, code, date):
    ids = lookup(state, scheme, code, date)
    assert len(ids) == 1, ids
    return ids[0]


# --- AC-1 -------------------------------------------------------------------


def test_ids_are_fixed_shape_and_deterministic():
    observations = [
        oa("9", iata="LHR", icao="EGLL", country="GB", lat=51.5, lon=-0.5),
        nasr("2.", "BBB", lat=36.0),
        nasr("1.", "AAA"),
    ]
    first = run((C1, observations))[0]
    second = run((C1, list(reversed(observations))))[0]
    assert first == second
    assert all(re.fullmatch(r"AP\d{7}", i) for i in first.identities)
    # NASR minted first, in site order; OurAirports after.
    assert only_id(first, "faa", "AAA", C1) == "AP0000001"
    assert only_id(first, "faa", "BBB", C1) == "AP0000002"
    assert only_id(first, "iata", "LHR", C1) == "AP0000003"


def test_ids_never_reused_or_removed():
    s1, s2, s3 = run(
        (C1, [nasr("1.", "AAA")]),
        (C2, [nasr("2.", "BBB", lat=40.0)]),
        (C3, [nasr("3.", "CCC", lat=45.0)]),
    )
    assert set(s1.identities) <= set(s2.identities) <= set(s3.identities)
    assert sorted(s3.identities) == ["AP0000001", "AP0000002", "AP0000003"]


def test_normalize_id_is_case_insensitive():
    assert normalize_id("ap0000123") == "AP0000123"
    with pytest.raises(ValueError):
        normalize_id("AP123")


# --- AC-2 -------------------------------------------------------------------


def test_rename_keeps_identity():
    s1, s2 = run(
        (C1, [nasr("06278.", "2Y1")]),
        (C2, [nasr("06278.", "47IA")]),
    )
    airport = only_id(s1, "faa", "2Y1", C1)
    assert only_id(s2, "faa", "47IA", C2) == airport
    assert only_id(s2, "faa", "2Y1", C1) == airport
    assert lookup(s2, "faa", "2Y1", C2) == []
    assert s2.identities[airport].match_basis == "nasr_site"


def test_site_number_correction_matches_by_faa_within_1nm():
    s1, s2 = run(
        (C1, [nasr("03329.19", "18AL")]),
        (C2, [nasr("00329.19", "18AL")]),
    )
    airport = only_id(s1, "faa", "18AL", C1)
    assert only_id(s2, "faa", "18AL", C2) == airport
    assert s2.identities[airport].nasr_site_no == "00329.19"
    assert s2.identities[airport].match_basis == "faa_lid_within_1nm"
    assert len(s2.identities) == 1


def test_site_number_correction_far_away_is_a_new_airport():
    _, s2 = run(
        (C1, [nasr("03329.19", "18AL")]),
        (C2, [nasr("00329.19", "18AL", lat=36.0)]),
    )
    assert len(s2.identities) == 2


def test_site_type_change_matches_by_site_number():
    s1, s2 = run(
        (C1, [nasr("17335.73", "40ND", site_type="A")]),
        (C2, [nasr("17335.73", "40ND", site_type="H")]),
    )
    airport = only_id(s1, "faa", "40ND", C1)
    assert only_id(s2, "faa", "40ND", C2) == airport
    assert s2.identities[airport].match_basis == "nasr_site_number"


def test_shared_site_number_across_types_stays_two_airports():
    cycle = [
        nasr("23747.31", "9XS4", site_type="A"),
        nasr("23747.31", "16XA", site_type="H", lat=35.001),
    ]
    s1, s2 = run((C1, cycle), (C2, cycle))
    assert len(s2.identities) == 2
    for code in ("9XS4", "16XA"):
        assert only_id(s1, "faa", code, C1) == only_id(s2, "faa", code, C2)


# --- AC-3 -------------------------------------------------------------------


def test_ourairports_attaches_to_nasr_and_pbi_becomes_djt():
    lat, lon = 26.68, -80.10
    s1, s2 = run(
        (C1, [nasr("03555.", "PBI", "KPBI", lat=lat, lon=lon),
              oa("3766", iata="PBI", icao="KPBI", lat=lat, lon=lon)]),
        (C2, [nasr("03555.", "DJT", "KDJT", lat=lat, lon=lon),
              oa("3766", iata="DJT", icao="KDJT", lat=lat, lon=lon)]),
    )
    assert len(s2.identities) == 1
    airport = only_id(s2, "iata", "DJT", C2)
    assert s2.identities[airport].ourairports_id == "3766"
    assert only_id(s2, "iata", "PBI", C1) == airport
    assert lookup(s2, "iata", "PBI", C2) == []
    assert only_id(s2, "icao", "KPBI", C1) == airport
    closed = [c for c in s2.codes if c.code == "PBI" and c.scheme == "iata"]
    assert [(c.effective_date, c.valid_to) for c in closed] == [(C1, C2)]


def test_ourairports_outside_jurisdiction_never_attaches_to_nasr():
    s1 = run((C1, [nasr("1.", "AAA", "KAAA"),
                   oa("5", icao="KAAA", country="CA")]))[0]
    assert len(s1.identities) == 2


def test_ourairports_far_from_nasr_does_not_attach():
    s1 = run((C1, [nasr("1.", "AAA", "KAAA"), oa("5", icao="KAAA", lat=45.0)]))[0]
    assert len(s1.identities) == 2


def test_attached_ourairports_icao_does_not_override_nasr():
    s1 = run((C1, [nasr("1.", "AAA", "KAAA"),
                   oa("5", iata="AAA", icao="KZZZ")]))[0]
    airport = only_id(s1, "faa", "AAA", C1)
    assert lookup(s1, "icao", "KZZZ", C1) == []
    assert only_id(s1, "iata", "AAA", C1) == airport


# --- AC-4 -------------------------------------------------------------------


def test_absent_is_not_closed_and_return_reuses_id():
    s1, s2, s3 = run(
        (C1, [nasr("1.", "NC52")]),
        (C2, []),
        (C3, [nasr("1.", "NC52")]),
    )
    airport = only_id(s1, "faa", "NC52", C1)
    assert s2.identities[airport].source_status == "operational"
    assert lookup(s2, "faa", "NC52", C2) == []
    assert [(p.effective_date, p.valid_to) for p in s2.presence] == [(C1, C2)]
    assert only_id(s3, "faa", "NC52", C3) == airport
    assert [(p.effective_date, p.valid_to) for p in s3.presence] == [
        (C1, C2), (C3, None),
    ]
    assert s3.identities[airport].last_seen_cycle == C3


def test_closure_only_from_source():
    s1 = run((C1, [nasr("1.", "AAA", status="closed_indefinitely")]))[0]
    airport = only_id(s1, "faa", "AAA", C1)
    assert s1.identities[airport].source_status == "closed_indefinitely"


# --- AC-5 -------------------------------------------------------------------


def test_history_is_append_only():
    states = run(
        (C1, [nasr("1.", "AAA"), nasr("2.", "BBB", lat=40.0)]),
        (C2, [nasr("1.", "AAB"), nasr("2.", "BBB", lat=40.0)]),
        (C3, [nasr("1.", "AAC")]),
    )
    for before, after in zip(states, states[1:], strict=False):
        closed = {c for c in before.codes if c.valid_to is not None}
        assert closed <= set(after.codes)
        closed_presence = {p for p in before.presence if p.valid_to is not None}
        assert closed_presence <= set(after.presence)


def test_convergence_aliases_higher_id_to_lower():
    # An OurAirports row in the US that shares no code with the NASR field
    # stands alone; once it does share one, the two identities converge.
    s1, s2 = run(
        (C1, [nasr("1.", "AAA", "KAAA"), oa("500", iata="XYZ")]),
        (C2, [nasr("1.", "AAA", "KAAA"), oa("500", iata="XYZ", icao="KAAA")]),
    )
    assert len(s1.identities) == 2
    assert s2.aliases == (Alias("AP0000002", "AP0000001", C2, "converged"),)
    assert only_id(s2, "iata", "XYZ", C2) == "AP0000001"
    assert only_id(s2, "iata", "XYZ", C1) == "AP0000002"


def test_alias_chain_is_rewritten_to_one_hop():
    s1 = run((C1, [nasr("1.", "AAA", "KAAA"), oa("500", iata="XYZ")]))[0]
    seeded = dataclasses.replace(
        s1, aliases=(Alias("AP0000009", "AP0000002", C1, "converged"),)
    )
    s2 = apply_cycle(
        seeded, C2, [nasr("1.", "AAA", "KAAA"), oa("500", iata="XYZ", icao="KAAA")]
    )
    targets = {a.alias_id: a.airport_id for a in s2.aliases}
    assert targets == {"AP0000009": "AP0000001", "AP0000002": "AP0000001"}
    assert not set(targets.values()) & set(targets)


def test_cycle_must_advance():
    s1 = run((C1, [nasr("1.", "AAA")]))[0]
    with pytest.raises(ValueError):
        apply_cycle(s1, C1, [nasr("1.", "AAA")])


# --- AC-6 -------------------------------------------------------------------


def test_lookup_is_case_insensitive_and_may_return_several():
    s1 = run((C1, [oa("1", iata="ABC", country="GB", lat=51.0, lon=0.0),
                   oa("2", iata="ABC", country="AU", lat=-33.0, lon=151.0)]))[0]
    assert len(lookup(s1, "IATA", "abc", C1)) == 2
    assert lookup(s1, "iata", "ABC", "2026-01-01") == []


def test_ourairports_attaches_to_a_nasr_field_in_the_same_foreign_country():
    """NASR lists some non-US fields (CYAM, MYNN...). The OurAirports row for
    the same field attaches when the countries match, so the ICAO code has one
    holder; a different country still never attaches."""
    field = dataclasses.replace(nasr("50000.", "CYAM", "CYAM"), iso_country="CA")
    same = run((C1, [field, oa("1657", iata="YAM", icao="CYAM", country="CA")]))[0]
    assert len(same.identities) == 1
    other = run((C1, [field, oa("1657", iata="YAM", icao="CYAM", country="BS")]))[0]
    assert len(other.identities) == 2


def test_nasr_legacy_country_an_matches_its_iso_successors():
    """NASR still files Sint Maarten (TNCM) under 'AN'; OurAirports uses SX."""
    field = dataclasses.replace(nasr("90875.", "TNCM", "TNCM"), iso_country="AN")
    state = run((C1, [field, oa("6406", iata="SXM", icao="TNCM", country="SX")]))[0]
    assert len(state.identities) == 1
    assert [i.iso_country for i in state.identities.values()] == ["SX"]


def test_an_identity_country_follows_the_real_history_in_cycle_order():
    """01-03 AC-5: NASR-only before OurAirports snapshots (NULL), then the
    attached SX row (SX), then the OA row absent (SX kept from before)."""
    field = dataclasses.replace(nasr("90875.", "TNCM", "TNCM"), iso_country="AN")
    sx = oa("6406", iata="SXM", icao="TNCM", country="SX")
    states = run((C1, [field]), (C2, [field, sx]), (C3, [field]))
    assert [[i.iso_country for i in s.identities.values()] for s in states] == [
        [None], ["SX"], ["SX"]]
    assert [len(s.identities) for s in states] == [1, 1, 1]


def test_a_non_successor_country_never_replaces_a_retired_code():
    """_can_pair also accepts an OA row filed under a US-jurisdiction country;
    that row states no AN successor, so the identity country is NULL."""
    field = dataclasses.replace(nasr("90875.", "TNCM", "TNCM"), iso_country="AN")
    state = run((C1, [field, oa("6406", iata="SXM", icao="TNCM", country="US")]))[0]
    assert len(state.identities) == 1
    assert [i.iso_country for i in state.identities.values()] == [None]


def test_a_current_nasr_country_is_written_unchanged():
    field = dataclasses.replace(nasr("50000.", "CYAM", "CYAM"), iso_country="CA")
    state = run((C1, [field, oa("1657", iata="YAM", icao="CYAM", country="CA")]))[0]
    assert [i.iso_country for i in state.identities.values()] == ["CA"]
    us = run((C1, [nasr("1.", "ABC")]))[0]
    assert [i.iso_country for i in us.identities.values()] == ["US"]


def test_an_ident_derived_icao_yields_to_an_explicit_icao_code():
    from aeronav_db.identity import ourairports_observations

    def row(oa_id, ident, icao_code, iata):
        return {"id": oa_id, "ident": ident, "type": "medium_airport",
                "name": ident, "latitude_deg": "27.2", "longitude_deg": "103.7",
                "iso_country": "CN", "icao_code": icao_code, "iata_code": iata}

    old, new = ourairports_observations(
        [row("32740", "ZPZT", "", ""), row("525773", "CN-0421", "ZPZT", "ZAT")]
    )
    assert old.codes == ()
    assert new.codes == (("iata", "ZAT"), ("icao", "ZPZT"))


# --- 02-01 AC-1: sticky attachment ----------------------------------------------

LAT, LON = 26.68, -80.10


def test_staggered_rename_keeps_one_id_without_an_alias():
    """NASR renames PBI -> DJT a cycle before OurAirports does. The known
    pairing (site 03555. <-> OurAirports 3766) holds while the codes disagree."""
    s1, s2, s3 = run(
        (C1, [nasr("03555.", "PBI", "KPBI", lat=LAT, lon=LON),
              oa("3766", iata="PBI", icao="KPBI", lat=LAT, lon=LON)]),
        (C2, [nasr("03555.", "DJT", "KDJT", lat=LAT, lon=LON),
              oa("3766", iata="PBI", icao="KPBI", lat=LAT, lon=LON)]),
        (C3, [nasr("03555.", "DJT", "KDJT", lat=LAT, lon=LON),
              oa("3766", iata="DJT", icao="KDJT", lat=LAT, lon=LON)]),
    )
    assert len(s3.identities) == 1 and s3.aliases == ()
    airport = only_id(s3, "faa", "DJT", C3)
    assert only_id(s3, "iata", "PBI", C2) == airport  # OurAirports' IATA, kept
    assert lookup(s3, "icao", "KPBI", C2) == []  # NASR is authoritative for ICAO
    assert only_id(s3, "iata", "DJT", C3) == airport


def test_not_sticky_when_out_of_range():
    s1, s2 = run(
        (C1, [nasr("1.", "AAA", "KAAA"), oa("5", iata="AAA", icao="KAAA")]),
        (C2, [nasr("1.", "AAB", "KAAB"), oa("5", iata="AAA", lat=45.0)]),
    )
    assert len(s2.identities) == 2


def test_not_sticky_when_the_row_now_shares_a_code_with_another_field():
    s1, s2 = run(
        (C1, [nasr("1.", "AAA", "KAAA"), nasr("2.", "BBB", "KBBB", lat=35.1),
              oa("5", iata="AAA", icao="KAAA")]),
        (C2, [nasr("1.", "AAC", "KAAC"), nasr("2.", "BBB", "KBBB", lat=35.1),
              oa("5", iata="BBB", icao="KBBB", lat=35.1)]),
    )
    bbb = only_id(s2, "faa", "BBB", C2)
    assert only_id(s2, "iata", "BBB", C2) == bbb


def test_a_standalone_ourairports_row_never_takes_a_code_nasr_assigns():
    """2024-04-18: OurAirports moved a duplicate of KCPF to 0,0, ident intact."""
    s1 = run((C1, [nasr("07191.1", "CPF", "KCPF"),
                   oa("348516", icao="KCPF", lat=0.004, lon=0.008)]))[0]
    assert len(s1.identities) == 2
    assert len(lookup(s1, "icao", "KCPF", C1)) == 1
    assert lookup(s1, "icao", "KCPF", C1) == lookup(s1, "faa", "CPF", C1)
