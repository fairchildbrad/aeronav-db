"""Backfill replay, driven by synthetic cached cycles. No network."""

from __future__ import annotations

import sqlite3

import pytest

from aeronav_db import backfill, build
from aeronav_db.identity import load_state

C = ["2020-03-26", "2020-04-23", "2020-05-21", "2020-06-18"]


def apt(site, faa, icao="", lat="35.0"):
    return {"SITE_NO": site, "SITE_TYPE_CODE": "A", "ARPT_ID": faa, "ICAO_ID": icao,
            "ARPT_NAME": faa, "ARPT_STATUS": "O", "LAT_DECIMAL": lat,
            "LONG_DECIMAL": "-80.0", "COUNTRY_CODE": "US"}


FIELDS = [apt(f"{i}.", f"A{i:02d}", lat=str(30 + i * 0.5)) for i in range(60)]


def install(monkeypatch, nasr_by_cycle, oa_from=None):
    def nasr_cycle(cache, cycle):
        rows = nasr_by_cycle.get(cycle)
        if rows is None:
            return None
        return {"format": "a", "sha256": f"sha-{cycle}", "url": f"u/{cycle}",
                "blank_status": [], "rows": rows}

    def snapshot(cache, commits, cycle):
        if oa_from is None or cycle < oa_from:
            return None
        return "c0ffee", [{"id": "9", "ident": "EGLL", "type": "large_airport",
                           "name": "Heathrow", "latitude_deg": "51.47",
                           "longitude_deg": "-0.46", "iso_country": "GB",
                           "icao_code": "EGLL", "iata_code": "LHR"}]

    monkeypatch.setattr(backfill, "nasr_cycle", nasr_cycle)
    monkeypatch.setattr(backfill, "ourairports_commits", lambda cache: [])
    monkeypatch.setattr(backfill, "ourairports_snapshot", snapshot)


def test_replay_skips_missing_cycles_and_starts_ourairports_mid_chain(
    tmp_path, monkeypatch
):
    renamed = [apt("0.", "B00")] + FIELDS[1:]
    install(monkeypatch, {C[0]: FIELDS, C[2]: FIELDS, C[3]: renamed}, oa_from=C[2])
    monkeypatch.setitem(backfill.ALLOWLIST, C[2], "first OurAirports snapshot (test)")
    state, meta, report = backfill.replay(tmp_path, C[0], C[3], log=lambda _: None)
    assert report["skipped"] == [C[1]]
    assert meta["history_start"] == C[0]
    assert meta["history_start_ourairports"] == C[2]
    assert [c["minted"] for c in report["cycles"]] == [60, 1, 0]

    seed = tmp_path / "seed.sqlite3"
    backfill.write_seed(seed, state, meta)
    connection = sqlite3.connect(seed)
    try:
        assert load_state(connection) == state
        assert connection.execute(
            "SELECT airport_id FROM airport_codes WHERE code = 'A00'"
        ).fetchone() == connection.execute(
            "SELECT airport_id FROM airport_codes WHERE code = 'B00'"
        ).fetchone()
    finally:
        connection.close()
    # The seed is a valid --previous-db.
    loaded, _, sha = build._load_previous(seed, False, tmp_path / "out.sqlite3",
                                          "2020-07-16")
    assert loaded == state and sha == build.sha256_of(seed)


def test_replay_is_deterministic(tmp_path, monkeypatch):
    install(monkeypatch, {C[0]: FIELDS, C[1]: FIELDS})
    first = backfill.replay(tmp_path, C[0], C[1], log=lambda _: None)
    second = backfill.replay(tmp_path, C[0], C[1], log=lambda _: None)
    assert first == second


def test_a_cycle_minting_too_many_ids_stops_the_replay(tmp_path, monkeypatch):
    # A column shift: every site number and identifier comes out garbled.
    broken = [apt(f"{i}.X", f"Z{i:02d}", lat=str(30 + i * 0.5)) for i in range(60)]
    install(monkeypatch, {C[0]: FIELDS, C[1]: broken})
    with pytest.raises(backfill.BackfillError, match="ALLOWLIST"):
        backfill.replay(tmp_path, C[0], C[1], log=lambda _: None)


def test_cycles_must_step_by_28_days():
    assert backfill.cycles(C[0], C[2]) == C[:3]
    with pytest.raises(backfill.BackfillError):
        backfill.cycles(C[0], "2020-05-22")
