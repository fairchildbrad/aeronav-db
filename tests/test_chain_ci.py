"""CI chain input: which previous file a build uses, and what it refuses."""

from __future__ import annotations

import json
import shutil

import pytest

from aeronav_db import build
from aeronav_db.chain import ChainError, Releases, resolve_previous
from tests.test_chain import CYCLE1, CYCLE2, run_build

S0, C1, C2 = "2026-06-11", "2026-07-09", "2026-08-06"


def release(releases_dir, cycle, database, manifest_path):
    target = releases_dir / f"cycle-{cycle}"
    target.mkdir(parents=True)
    shutil.copy(database, target / "navigation.sqlite3")
    shutil.copy(manifest_path, target / "manifest.json")
    (target / "navigation.sqlite3.sha256").write_text(
        f"{build.sha256_of(database)}  navigation.sqlite3\n"
    )
    return target


@pytest.fixture
def world(tmp_path):
    """A seed at S0 and a schema-3 release at C1 chained from it."""
    work = tmp_path / "work"
    work.mkdir()
    seed = work / "seed" / "navigation.sqlite3"
    seed.parent.mkdir()
    run_build(work, S0, *CYCLE1, seed, bootstrap=True)
    pin = {"cycle": S0, "sha256": build.sha256_of(seed), "url": "unused"}
    c1_dir = work / "c1"
    c1_dir.mkdir()
    c1 = c1_dir / "navigation.sqlite3"
    run_build(work, C1, *CYCLE1, c1, previous_db=seed)
    return {"tmp": tmp_path, "work": work, "seed": seed, "pin": pin, "c1": c1,
            "releases": tmp_path / "releases"}


def resolve(world, cycle, **kwargs):
    world["releases"].mkdir(exist_ok=True)
    return resolve_previous(
        cycle, Releases.from_dir(world["releases"]), world["tmp"] / "prev",
        pin=world["pin"], seed_path=world["seed"], **kwargs,
    )


def test_no_schema3_release_uses_the_pinned_seed(world):
    assert resolve(world, C1)["source"] == "seed"


def test_a_schema2_release_is_never_used(world):
    target = release(world["releases"], C1, world["c1"],
                     world["c1"].with_suffix(".json"))
    manifest = json.loads((target / "manifest.json").read_text())
    manifest["schema_version"] = "2"
    (target / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ChainError, match="56 days"):
        resolve(world, C2)


def test_the_newest_older_schema3_release_is_used_with_lineage(world):
    release(world["releases"], C1, world["c1"], world["c1"].with_suffix(".json"))
    provenance = resolve(world, C2)
    assert provenance == {"source": f"release cycle-{C1}", "cycle": C1,
                          "sha256": build.sha256_of(world["c1"])}
    assert build.sha256_of(world["tmp"] / "prev" / "previous.sqlite3") == \
        provenance["sha256"]


def test_a_forced_rebuild_of_n_chains_from_n_minus_1(world):
    release(world["releases"], C1, world["c1"], world["c1"].with_suffix(".json"))
    assert resolve(world, C1)["source"] == "seed"


def test_rebuilding_n_when_a_newer_release_exists_is_refused(world):
    release(world["releases"], C1, world["c1"], world["c1"].with_suffix(".json"))
    with pytest.raises(ChainError, match="fork the lineage"):
        resolve(world, S0)


def test_a_database_not_matching_its_manifest_is_refused(world):
    target = release(world["releases"], C1, world["c1"],
                     world["c1"].with_suffix(".json"))
    (target / "navigation.sqlite3").write_bytes(b"tampered")
    with pytest.raises(ChainError, match="does not match its manifest"):
        resolve(world, C2)
    assert not (world["tmp"] / "prev" / "previous.sqlite3").exists()


def test_a_swapped_database_with_an_edited_manifest_fails_lineage(world):
    """A coordinated swap passes the hash checks but not the parent hash."""
    rogue = world["work"] / "rogue" / "navigation.sqlite3"
    rogue.parent.mkdir()
    run_build(world["work"], C1, *CYCLE2, rogue, bootstrap=True)
    target = release(world["releases"], C1, rogue, rogue.with_suffix(".json"))
    assert json.loads((target / "manifest.json").read_text())["database"]["sha256"] \
        == build.sha256_of(rogue)
    with pytest.raises(ChainError, match="parent"):
        resolve(world, C2)


def test_a_seed_not_matching_its_pin_is_refused(world):
    world["pin"]["sha256"] = "0" * 64
    with pytest.raises(ChainError, match="does not match the pin"):
        resolve(world, C1)


def test_a_gap_is_refused_unless_allowed(world):
    with pytest.raises(ChainError, match="--allow-gap"):
        resolve(world, C2)
    assert resolve(world, C2, allow_gap=True)["gap_days"] == 56


def test_no_release_and_no_pin_is_refused(world):
    world["pin"] = None
    with pytest.raises(ChainError, match="no seed pin"):
        resolve(world, C1)


def test_the_pin_matches_the_local_seed_when_present():
    from pathlib import Path
    pin = json.loads(Path("identity/seed.json").read_text())
    local = Path("dist/backfill/seed.sqlite3")
    if not local.exists():
        pytest.skip("no local seed")
    assert build.sha256_of(local) == pin["sha256"]
    import sqlite3
    with sqlite3.connect(f"file:{local}?mode=ro", uri=True) as connection:
        (cycle,) = connection.execute(
            "SELECT value FROM metadata WHERE key = 'airac_cycle'").fetchone()
    assert pin["cycle"] == cycle
    if pin["published"] is True:
        # After runbook step 5 the pin names the uploaded release asset.
        assert pin["url"] == (
            "https://github.com/fairchildbrad/aeronav-db/releases/download/"
            f"identity-seed-{pin['cycle']}/seed.sqlite3")
    else:
        assert pin["published"] is False  # before step 5: not yet uploaded
