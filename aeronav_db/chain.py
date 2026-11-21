"""Pick, fetch and check the file cycle N is chained from.

    python -m aeronav_db.chain previous --cycle 2026-11-26 --out prev/

The previous file is either:

(a) the newest release ``cycle-D``, with D < N, whose manifest says schema 3.
    Its database must match both the manifest's sha256 and the release's
    .sha256 asset, and its own parent hash must chain to the release (or
    seed) before it. Or:
(b) when no schema-3 release exists yet, the seed pinned in identity/seed.json.

It refuses rather than guess:
- any hash mismatch;
- a gap (the previous file is not N-28) unless ``--allow-gap``;
- a rebuild of N when a newer schema-3 release exists, which would fork the
  lineage that release recorded.

Until GitHub immutable releases are enabled, path (a) trusts the release's
manifest plus its .sha256 asset, and the one-hop lineage check is the backstop
against a swapped file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from aeronav_db.nasr_archive import RETRIES
from aeronav_db.verify import check_identity, retired_country_note

TAG_RE = re.compile(r"^cycle-(\d{4}-\d{2}-\d{2})$")
DEFAULT_REPO = "fairchildbrad/aeronav-db"
DEFAULT_PIN = Path(__file__).resolve().parent.parent / "identity" / "seed.json"
CYCLE_DAYS = 28
# Every network call made, for the record (the dry run pastes this).
CALLS: list[str] = []


class ChainError(Exception):
    pass


def _download(url: str) -> bytes:
    headers = {"User-Agent": "aeronav-db-chain", "Accept": "application/octet-stream"}
    if "api.github.com" in url:
        headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    CALLS.append(f"GET {url}")
    for attempt in range(RETRIES):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310
                expected = response.headers.get("Content-Length")
                data = response.read()
            if expected is not None and len(data) != int(expected):
                raise ChainError(f"short read from {url}")
            return data
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == RETRIES - 1:
                raise ChainError(f"{url}: HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == RETRIES - 1:
                raise ChainError(f"{url}: {error}") from error
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


class Releases:
    """``{cycle: {asset name: fetch()}}`` for cycle-D releases."""

    def __init__(self, assets: dict[str, dict[str, object]]) -> None:
        self.assets = assets

    @classmethod
    def from_github(cls, repo: str) -> Releases:
        found: dict[str, dict[str, object]] = {}
        page = 1
        while True:
            batch = json.loads(_download(
                f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
            ))
            for release in batch:
                match = TAG_RE.match(release["tag_name"])
                if match and not release.get("prerelease") and not release.get("draft"):
                    found[match.group(1)] = {
                        a["name"]: (lambda u=a["browser_download_url"]: _download(u))
                        for a in release["assets"]
                    }
            if len(batch) < 100:
                return cls(found)
            page += 1

    @classmethod
    def from_dir(cls, directory: Path) -> Releases:
        """DIR/cycle-D/<assets>: for tests and dry runs."""
        found: dict[str, dict[str, object]] = {}
        for release in sorted(directory.iterdir()):
            match = TAG_RE.match(release.name)
            if match:
                found[match.group(1)] = {
                    p.name: (lambda p=p: p.read_bytes()) for p in release.iterdir()
                }
        return cls(found)

    def manifest(self, cycle: str) -> dict:
        fetch = self.assets[cycle].get("manifest.json")
        return json.loads(fetch()) if fetch else {}  # type: ignore[operator]

    def get(self, cycle: str, name: str) -> bytes:
        fetch = self.assets[cycle].get(name)
        if fetch is None:
            raise ChainError(f"release cycle-{cycle} has no {name}")
        return fetch()  # type: ignore[operator]


def _metadata(path: Path) -> dict[str, str]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return dict(connection.execute("SELECT key, value FROM metadata"))
    finally:
        connection.close()


def _identity_problems(path: Path) -> list[str]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        note = retired_country_note(connection, str(path))
        if note:
            print(note, file=sys.stderr)
        return check_identity(connection)[0]
    finally:
        connection.close()


def resolve_previous(
    cycle: str,
    releases: Releases,
    out_dir: Path,
    *,
    pin: dict | None,
    seed_path: Path | None = None,
    allow_gap: bool = False,
) -> dict:
    """Write out_dir/previous.sqlite3 and return its provenance."""
    schema3 = {}
    for day in sorted(releases.assets, reverse=True):
        manifest = releases.manifest(day)
        if str(manifest.get("schema_version")) == "3":
            schema3[day] = manifest
    newer = sorted(d for d in schema3 if d > cycle)
    if newer:
        raise ChainError(
            f"schema-3 releases newer than {cycle} exist ({newer}); rebuilding "
            f"{cycle} would fork the lineage they recorded"
        )
    older = sorted(d for d in schema3 if d < cycle)
    out_dir.mkdir(parents=True, exist_ok=True)
    staging = out_dir / "previous.sqlite3.partial"

    if older:
        day = older[-1]
        manifest = schema3[day]
        data = releases.get(day, manifest["database"]["filename"])
        digest = hashlib.sha256(data).hexdigest()
        sidecar = releases.get(day, manifest["database"]["filename"] + ".sha256")
        if digest != manifest["database"]["sha256"]:
            raise ChainError(f"cycle-{day}: database does not match its manifest")
        if digest != sidecar.decode().split()[0]:
            raise ChainError(f"cycle-{day}: database does not match its .sha256 asset")
        provenance = {"source": f"release cycle-{day}", "cycle": day, "sha256": digest}
    else:
        if not pin:
            raise ChainError("no schema-3 release before this cycle and no seed pin")
        if seed_path is None and pin.get("published") is not True:
            raise ChainError(
                "the first schema-3 release chains from the seed, which is not "
                "published yet (identity/seed.json published=false). Seed upload "
                "is an operator-confirmed step: see docs/RELEASE-RUNBOOK.md"
            )
        data = (
            seed_path.read_bytes()
            if seed_path is not None
            else _download(pin["url"])
        )
        digest = hashlib.sha256(data).hexdigest()
        if digest != pin["sha256"]:
            raise ChainError(f"seed sha256 {digest} does not match the pin")
        provenance = {"source": "seed", "cycle": pin["cycle"], "sha256": digest,
                      "url": pin["url"]}

    staging.write_bytes(data)
    try:
        meta = _metadata(staging)
        if meta.get("airac_cycle") != provenance["cycle"]:
            raise ChainError(
                f"{provenance['source']}: file says cycle {meta.get('airac_cycle')}, "
                f"expected {provenance['cycle']}"
            )
        if meta.get("schema_version") != "3":
            raise ChainError(f"{provenance['source']}: not schema 3")
        problems = _identity_problems(staging)
        if problems:
            raise ChainError(f"{provenance['source']}: " + "; ".join(problems))
        parent_cycle = meta.get("previous_cycle", "")
        parent_sha = meta.get("previous_db_sha256", "")
        if older:
            # One-hop lineage: the parent hash must chain to what was published.
            if parent_cycle in schema3:
                expected = schema3[parent_cycle]["database"]["sha256"]
            elif pin and parent_cycle == pin["cycle"]:
                expected = pin["sha256"]
            else:
                raise ChainError(
                    f"{provenance['source']}: parent {parent_cycle!r} is neither a "
                    "schema-3 release nor the pinned seed"
                )
            if parent_sha != expected:
                raise ChainError(
                    f"{provenance['source']}: parent hash does not chain to "
                    f"{parent_cycle}"
                )
        gap = (date.fromisoformat(cycle) - date.fromisoformat(provenance["cycle"])).days
        if gap != CYCLE_DAYS:
            if not allow_gap:
                raise ChainError(
                    f"previous file is cycle {provenance['cycle']}, {gap} days before "
                    f"{cycle}: build {date.fromisoformat(cycle) - timedelta(days=28)} "
                    "first, or pass --allow-gap"
                )
            provenance["gap_days"] = gap
    except Exception:
        staging.unlink()
        raise
    staging.replace(out_dir / "previous.sqlite3")
    (out_dir / "previous.json").write_text(json.dumps(provenance, indent=1) + "\n")
    return provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the chain input.")
    sub = parser.add_subparsers(dest="command", required=True)
    previous = sub.add_parser("previous")
    previous.add_argument("--cycle", required=True)
    previous.add_argument("--out", required=True)
    previous.add_argument("--repo", default=DEFAULT_REPO)
    previous.add_argument("--releases-dir", help="Read releases from disk instead.")
    previous.add_argument("--seed-pin", default=str(DEFAULT_PIN))
    previous.add_argument(
        "--seed-path", help="Local seed file instead of the pin's url."
    )
    previous.add_argument("--allow-gap", action="store_true")
    args = parser.parse_args(argv)

    pin_path = Path(args.seed_pin)
    pin = json.loads(pin_path.read_text()) if pin_path.exists() else None
    try:
        releases = (
            Releases.from_dir(Path(args.releases_dir))
            if args.releases_dir
            else Releases.from_github(args.repo)
        )
        provenance = resolve_previous(
            args.cycle, releases, Path(args.out), pin=pin,
            seed_path=Path(args.seed_path) if args.seed_path else None,
            allow_gap=args.allow_gap,
        )
    except ChainError as error:
        print(f"CHAIN REFUSED: {error}", file=sys.stderr)
        for call in CALLS:
            print(f"  {call}", file=sys.stderr)
        return 2
    print(json.dumps(provenance))
    for call in CALLS:
        print(f"  {call}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
