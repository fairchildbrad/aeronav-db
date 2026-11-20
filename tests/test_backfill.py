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


# --- Internet Archive fallback (02-03) -------------------------------------------

CDX = (b'[["timestamp","digest","length"],'
       b'["20201029194455","AAA","1"],["20210325204726","BBB","1"]]')


def test_wayback_source_takes_the_newest_capture_and_lists_digests(monkeypatch):
    monkeypatch.setattr(backfill, "_get", lambda url, headers=None: CDX)
    found = backfill.wayback_source("https://nfdc.faa.gov/x.zip")
    assert found["capture"] == "20210325204726"
    assert found["fetch_url"] == (
        "https://web.archive.org/web/20210325204726id_/https://nfdc.faa.gov/x.zip"
    )
    assert found["digests"] == ["AAA", "BBB"] and found["captures"] == 2


def test_wayback_offline_page_is_retried_not_parsed(monkeypatch):
    answers = iter([b"<html>Temporarily Offline</html>", CDX])
    monkeypatch.setattr(backfill, "_get", lambda url, headers=None: next(answers))
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)
    assert backfill.wayback_source("u")["capture"] == "20210325204726"


def test_no_capture_means_missing(monkeypatch):
    monkeypatch.setattr(backfill, "_get", lambda url, headers=None: b"[]")
    assert backfill.wayback_source("u") is None


def test_faa_404_falls_back_to_wayback_and_records_provenance(monkeypatch, tmp_path):
    import io
    import urllib.error
    import zipfile

    def apt_rows(url):
        if str(url).startswith("https://"):
            raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO())
        return "a", [apt("1.", "A01")], b"raw"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("APT.txt", "x")

    def get(url, headers=None):
        return buffer.getvalue() if "id_/" in url else CDX

    monkeypatch.setattr(backfill.nasr_archive, "apt_rows", apt_rows)
    monkeypatch.setattr(backfill.nasr_archive, "legacy_blank_status", lambda raw: [])
    monkeypatch.setattr(backfill, "_get", get)
    monkeypatch.setattr(backfill.time, "sleep", lambda s: None)
    meta = backfill.nasr_cycle(tmp_path, "2019-09-12")
    assert meta["source"] == "wayback" and meta["capture"] == "20210325204726"
    again = backfill.nasr_cycle(tmp_path, "2019-09-12")
    assert again["source"] == "wayback" and len(again["rows"]) == 1


# --- 01-03: retired NASR country codes ---------------------------------------


def _with_an(state):
    import dataclasses

    from aeronav_db.identity import IdentityState
    first = sorted(state.identities)[0]
    identities = dict(state.identities)
    identities[first] = dataclasses.replace(identities[first], iso_country="AN")
    return IdentityState(identities, state.codes, state.presence, state.aliases,
                         state.next_id, state.last_cycle)


def test_write_seed_refuses_a_retired_country(tmp_path, monkeypatch):
    install(monkeypatch, {C[0]: FIELDS})
    state, meta, _ = backfill.replay(tmp_path, C[0], C[0], log=lambda _: None)
    seed = tmp_path / "seed.sqlite3"
    with pytest.raises(backfill.BackfillError, match="retired NASR country"):
        backfill.write_seed(seed, _with_an(state), meta)
    assert not seed.exists()


def test_replay_refuses_a_cycle_whose_state_carries_a_retired_country(
    tmp_path, monkeypatch
):
    install(monkeypatch, {C[0]: FIELDS, C[1]: FIELDS})
    real = backfill.identity.apply_cycle

    def apply_cycle(state, date, observations):
        out = real(state, date, observations)
        return _with_an(out) if date == C[1] else out

    monkeypatch.setattr(backfill.identity, "apply_cycle", apply_cycle)
    with pytest.raises(backfill.BackfillError, match="retired NASR country"):
        backfill.replay(tmp_path, C[0], C[1], log=lambda _: None)
