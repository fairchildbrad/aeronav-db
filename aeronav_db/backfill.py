"""Replay archived history into a seed file the first schema-3 release chains from.

    python -m aeronav_db.backfill --from 2020-03-26 --to 2026-10-01 \\
        --cache ~/.cache/aeronav-backfill --out seed.sqlite3

Every NASR cycle in the archive, oldest first, plus the OurAirports
airports.csv as it stood the day before each cycle (git history starts
2021-11-02; before that the chain is NASR-only), goes through the same
``apply_cycle`` the weekly build uses. Ids minted here are permanent, so:

* everything fetched is cached, and lineage records the sha256 of the exact
  bytes parsed and the OurAirports commit;
* each step must pass ``check_chain`` against the one before;
* a cycle that mints or closes more than ANOMALY_FRACTION of the airports
  stops the replay unless ALLOWLIST names it with a reason, because a parser
  slip at a format change would otherwise mint thousands of permanent ids.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from aeronav_db import identity, nasr_archive
from aeronav_db.build import DISCLAIMER, LICENCE, SCHEMA, SCHEMA_VERSION, sha256_of
from aeronav_db.cycle import BROWSER_USER_AGENT, NASR_URL_TEMPLATE
from aeronav_db.verify import check_chain, check_identity

CYCLE_DAYS = 28
ANOMALY_FRACTION = 0.02
# Cycles allowed past the anomaly guard, each with the reason.
ALLOWLIST = {
    "2021-11-04": "first OurAirports snapshot (git history starts 2021-11-02): "
    "every non-US airport is new",
}
OURAIRPORTS_REPO = "davidmegginson/ourairports-data"
OURAIRPORTS_RAW = (
    "https://raw.githubusercontent.com/" + OURAIRPORTS_REPO + "/{sha}/airports.csv"
)
OURAIRPORTS_COMMITS = (
    "https://api.github.com/repos/" + OURAIRPORTS_REPO
    + "/commits?path=airports.csv&since={since}&until={until}&per_page=100&page={page}"
)
# The mirror's history starts here; the API caps deep paging (HTTP 422), so
# the commit list is fetched in quarterly windows.
OURAIRPORTS_HISTORY_START = date(2021, 10, 1)


class BackfillError(Exception):
    pass


def cycles(start: str, end: str) -> list[str]:
    day, last = date.fromisoformat(start), date.fromisoformat(end)
    out = []
    while day <= last:
        out.append(day.isoformat())
        day += timedelta(days=CYCLE_DAYS)
    if out[-1] != end:
        raise BackfillError(f"{end} is not a 28-day step from {start}")
    return out


def _get(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": BROWSER_USER_AGENT, **(headers or {})}
    )
    for attempt in range(nasr_archive.RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == nasr_archive.RETRIES - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == nasr_archive.RETRIES - 1:
                raise
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


# --- Internet Archive fallback -----------------------------------------------
# The FAA serves 28-day files from 2020-03-26 on. Earlier cycles survive as
# Wayback captures of the same FAA URL; the bytes are the FAA's (checked on the
# 2020-03-26 overlap, which both serve). The Archive is only the carrier.
WAYBACK_CDX = (
    "https://web.archive.org/cdx/search/cdx?url={url}"
    "&filter=statuscode:200&fl=timestamp,digest,length&output=json"
)
WAYBACK_RAW = "https://web.archive.org/web/{timestamp}id_/{url}"


def wayback_captures(url: str) -> list[dict[str, str]]:
    """200 captures of exactly ``url``, oldest first. The Archive answers
    'Temporarily Offline' with an HTML page, which is retried, never parsed."""
    for attempt in range(nasr_archive.RETRIES):
        body = _get(WAYBACK_CDX.format(url=url))
        try:
            table = json.loads(body) if body.strip() else []
        except json.JSONDecodeError:
            if attempt == nasr_archive.RETRIES - 1:
                raise BackfillError(f"Wayback CDX unavailable for {url}") from None
            time.sleep(30 * (attempt + 1))
            continue
        if not table:
            return []
        header, *rows = table
        return [dict(zip(header, row)) for row in rows]
    raise AssertionError("unreachable")


def wayback_source(url: str) -> dict | None:
    """The newest capture, plus every distinct digest seen (an FAA re-post
    shows as more than one)."""
    captures = wayback_captures(url)
    if not captures:
        return None
    newest = captures[-1]
    return {
        "source": "wayback",
        "capture": newest["timestamp"],
        "fetch_url": WAYBACK_RAW.format(timestamp=newest["timestamp"], url=url),
        "digests": sorted({c["digest"] for c in captures}),
        "captures": len(captures),
    }


# --- Cache ---------------------------------------------------------------------


def nasr_cycle(cache: Path, cycle: str) -> dict | None:
    """Cached {format, sha256, url, blank_status, rows} or None if the cycle
    is not in the archive (404)."""
    meta_path = cache / "nasr" / f"{cycle}.json"
    rows_path = cache / "nasr" / f"{cycle}.csv.gz"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("missing"):
            return None
        with gzip.open(rows_path, "rt", encoding="utf-8", newline="") as handle:
            meta["rows"] = list(csv.DictReader(handle))
        return meta
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    url = NASR_URL_TEMPLATE.format(cycle=cycle)
    provenance: dict = {"source": "faa"}
    try:
        fmt, rows, raw = nasr_archive.apt_rows(url)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        wayback = wayback_source(url)
        if wayback is None:
            meta_path.write_text(json.dumps({"missing": True, "url": url}))
            return None
        provenance = wayback
        fmt, rows, raw = nasr_archive.apt_rows(wayback["fetch_url"])
    blank = nasr_archive.legacy_blank_status(raw) if fmt == "a" else []
    with gzip.open(rows_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=nasr_archive.APT_COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    meta = {"format": fmt, "sha256": hashlib.sha256(raw).hexdigest(), "url": url,
            "blank_status": blank, **provenance}
    meta_path.write_text(json.dumps(meta, indent=1))
    meta["rows"] = rows
    return meta


def ourairports_commits(cache: Path) -> list[tuple[str, str]]:
    """[(committer ISO date, sha)] for airports.csv, oldest first."""
    path = cache / "ourairports" / "commits.json"
    if path.exists():
        return [tuple(c) for c in json.loads(path.read_text())]
    path.parent.mkdir(parents=True, exist_ok=True)
    commits: list[tuple[str, str]] = []
    window = OURAIRPORTS_HISTORY_START
    today = date.today()
    while window <= today:
        until = window + timedelta(days=92)
        page = 1
        while True:
            batch = json.loads(_get(
                OURAIRPORTS_COMMITS.format(
                    since=f"{window}T00:00:00Z", until=f"{until}T00:00:00Z", page=page
                ),
                {"Accept": "application/vnd.github+json"},
            ))
            commits += [(c["commit"]["committer"]["date"], c["sha"]) for c in batch]
            if len(batch) < 100:
                break
            page += 1
        window = until
    commits = sorted(set(commits))
    commits.sort()
    path.write_text(json.dumps(commits))
    return commits


def ourairports_snapshot(
    cache: Path, commits: list[tuple[str, str]], cycle: str
) -> tuple[str, list[dict[str, str]]] | None:
    """The airports.csv of the last commit before the cycle date, or None."""
    before = [sha for when, sha in commits if when < f"{cycle}T00:00:00Z"]
    if not before:
        return None
    sha = before[-1]
    path = cache / "ourairports" / f"{sha}.csv.gz"
    if not path.exists():
        path.write_bytes(gzip.compress(_get(OURAIRPORTS_RAW.format(sha=sha)), mtime=0))
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    return sha, list(csv.DictReader(io.StringIO(text)))


# --- Replay --------------------------------------------------------------------


def _state_db(
    state: identity.IdentityState, previous_cycle: str = ""
) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    identity.dump_state(connection, state)
    connection.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        {
            "airac_cycle": state.last_cycle or "",
            "airport_id_next": str(state.next_id),
            "history_start": "",
            "previous_cycle": previous_cycle,
            "previous_db_sha256": "",
        }.items(),
    )
    return connection


def replay(cache: Path, start: str, end: str, *, log=print) -> tuple:
    commits = ourairports_commits(cache)
    state = identity.IdentityState.empty()
    previous_db = None
    sources, skipped, report_cycles = [], [], []
    history_start = history_start_oa = ""
    for cycle in cycles(start, end):
        nasr = nasr_cycle(cache, cycle)
        if nasr is None:
            skipped.append(cycle)
            log(f"{cycle}: not in the archive, skipped")
            continue
        snapshot = ourairports_snapshot(cache, commits, cycle)
        observations = identity.nasr_observations(nasr["rows"])
        if snapshot is not None:
            observations += identity.ourairports_observations(snapshot[1])
            history_start_oa = history_start_oa or cycle
        before = state
        state = identity.apply_cycle(state, cycle, observations)
        history_start = history_start or cycle

        minted = state.next_id - before.next_id
        closed = sum(1 for p in state.presence if p.valid_to == cycle)
        nasr_count = len(nasr["rows"])
        if before.last_cycle is not None and (
            max(minted, closed) > ANOMALY_FRACTION * nasr_count
        ) and cycle not in ALLOWLIST:
            raise BackfillError(
                f"{cycle}: {minted} minted, {closed} presence closed, against "
                f"{nasr_count} NASR rows (> {ANOMALY_FRACTION:.0%}). Check the "
                "parse; if genuine, add the cycle to ALLOWLIST with a reason."
            )

        current_db = _state_db(state, before.last_cycle or "")
        problems, _ = check_identity(current_db)
        if previous_db is not None:
            problems += check_chain(current_db, previous_db, "")
        if problems:
            raise BackfillError(f"{cycle}: " + "; ".join(problems))
        previous_db = current_db

        basis: dict[str, int] = {}
        for record in state.identities.values():
            if record.last_seen_cycle == cycle:
                basis[record.match_basis] = basis.get(record.match_basis, 0) + 1
        iata_shared = current_db.execute(
            "SELECT code, group_concat(airport_id) FROM airport_codes "
            "WHERE scheme = 'iata' AND valid_to IS NULL GROUP BY code "
            "HAVING count(DISTINCT airport_id) > 1 ORDER BY code"
        ).fetchall()
        countries = sorted({r.get("COUNTRY_CODE", "") for r in nasr["rows"]})
        report_cycles.append({
            "cycle": cycle, "format": nasr["format"], "nasr_rows": nasr_count,
            "ourairports_commit": snapshot[0] if snapshot else None,
            "minted": minted, "presence_closed": closed, "match_basis": basis,
            "aliases_new": [
                [a.alias_id, a.airport_id] for a in state.aliases
                if a.effective_date == cycle
            ],
            "nasr_blank_status": nasr["blank_status"],
            "nasr_countries": countries,
            "iata_shared": [list(row) for row in iata_shared],
            "allowlisted": ALLOWLIST.get(cycle),
        })
        sources.append({"cycle": cycle, "nasr_url": nasr["url"],
                        "nasr_sha256": nasr["sha256"], "nasr_format": nasr["format"],
                        "ourairports_commit": snapshot[0] if snapshot else None,
                        "nasr_carrier": nasr.get("source", "faa"),
                        **({"wayback_capture": nasr["capture"]}
                           if nasr.get("source") == "wayback" else {})})
        log(f"{cycle}: fmt {nasr['format']} rows {nasr_count} minted {minted} "
            f"closed {closed} aliases {len(state.aliases)} iata_shared "
            f"{len(iata_shared)}")
    meta = {
        "history_start": history_start,
        "history_start_ourairports": history_start_oa,
        "backfill_sources": json.dumps(sources, separators=(",", ":")),
        "skipped_cycles": json.dumps(skipped),
    }
    return state, meta, {"cycles": report_cycles, "skipped": skipped}


def write_seed(path: Path, state: identity.IdentityState, meta: dict[str, str]) -> None:
    """A schema-3 file holding identity history only, for ``--previous-db``."""
    staging = path.with_name(path.name + ".partial")
    if staging.exists():
        staging.unlink()
    connection = sqlite3.connect(staging)
    try:
        connection.executescript(SCHEMA)
        identity.dump_state(connection, state)
        metadata = {
            "airac_cycle": state.last_cycle or "",
            "schema_version": SCHEMA_VERSION,
            "airport_id_next": str(state.next_id),
            "previous_cycle": "",
            "previous_db_sha256": "",
            "sources": (
                "FAA NASR archive (and FAA NASR files preserved by the "
                "Internet Archive); OurAirports git history"
            ),
            "licence": LICENCE,
            "disclaimer": DISCLAIMER,
            "generator": "aeronav_db.backfill",
            **meta,
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)", sorted(metadata.items())
        )
        connection.commit()
        connection.execute("VACUUM")
        problems, _ = check_identity(connection)
    finally:
        connection.close()
    if problems:
        staging.unlink()
        raise BackfillError("seed fails its invariants: " + "; ".join(problems))
    staging.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay archived airport history.")
    parser.add_argument("--from", dest="start", default="2020-03-26")
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", help="JSON report path (default: OUT.report.json)")
    args = parser.parse_args(argv)
    started = datetime.now()
    try:
        state, meta, report = replay(Path(args.cache), args.start, args.end)
        out = Path(args.out)
        write_seed(out, state, meta)
    except BackfillError as error:
        print(f"BACKFILL STOPPED: {error}", file=sys.stderr)
        return 2
    report["seed_sha256"] = sha256_of(out)
    report["identities"] = len(state.identities)
    report["aliases"] = len(state.aliases)
    Path(args.report or f"{out}.report.json").write_text(json.dumps(report, indent=1))
    print(f"wrote {out}: {len(state.identities)} ids, {len(state.aliases)} aliases, "
          f"sha256 {report['seed_sha256']} ({datetime.now() - started})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
