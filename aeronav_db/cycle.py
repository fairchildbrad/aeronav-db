"""AIRAC cycle arithmetic and discovery of the newest published FAA cycle.

Aeronautical data worldwide is published on a 28-day AIRAC cycle, with each
edition taking effect at 00:00 UTC on its effective date. The FAA publishes the
next cycle some weeks ahead of that date, so "newest downloadable" and "newest
in force" are different questions. This module answers both, and the build only
ever ships a cycle that is actually in force.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from datetime import date, timedelta

# A known-good AIRAC effective date. Every other cycle is a multiple of 28 days
# away from it, in either direction.
AIRAC_ANCHOR = date(2026, 7, 9)
AIRAC_DAYS = 28

NASR_URL_TEMPLATE = (
    "https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_{cycle}.zip"
)

# nfdc.faa.gov answers a default urllib/curl user agent with HTTP 503.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def current_cycle(today: date | None = None) -> date:
    """The AIRAC effective date in force on `today`."""
    today = today or date.today()
    elapsed = (today - AIRAC_ANCHOR).days
    # Floor division handles dates before the anchor correctly in Python.
    return AIRAC_ANCHOR + timedelta(days=(elapsed // AIRAC_DAYS) * AIRAC_DAYS)


def next_cycle(after: date | None = None) -> date:
    return current_cycle(after) + timedelta(days=AIRAC_DAYS)


def recent_cycles(count: int = 4, today: date | None = None) -> list[date]:
    """The current cycle and the `count - 1` before it, newest first."""
    latest = current_cycle(today)
    return [latest - timedelta(days=AIRAC_DAYS * step) for step in range(count)]


def nasr_url(cycle: date) -> str:
    return NASR_URL_TEMPLATE.format(cycle=cycle.isoformat())


def is_published(cycle: date, *, timeout: int = 60) -> bool:
    """Whether the FAA is currently serving this cycle's subscription zip.

    Probes with a one-byte ranged GET rather than HEAD: nfdc.faa.gov answers
    every HEAD with 503, so a HEAD-based check reports "nothing is published"
    even when everything is.
    """
    request = urllib.request.Request(
        nasr_url(cycle),
        headers={"User-Agent": BROWSER_USER_AGENT, "Range": "bytes=0-0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return 200 <= response.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def latest_available_cycle(today: date | None = None, *, lookback: int = 4) -> date:
    """The newest in-force cycle the FAA is actually serving.

    Walks backwards from the current cycle. A cycle that is in force but not yet
    mirrored (or briefly unavailable) falls through to the one before it rather
    than failing the build.
    """
    for candidate in recent_cycles(lookback, today):
        if is_published(candidate):
            return candidate
    raise RuntimeError(
        "no published NASR cycle found in the last "
        f"{lookback} cycles (checked back to {recent_cycles(lookback, today)[-1]})"
    )


def main(argv: list[str] | None = None) -> int:
    """Print the newest in-force cycle the FAA is serving, for CI to consume."""
    import argparse

    parser = argparse.ArgumentParser(description="Report AIRAC cycles.")
    parser.add_argument(
        "--latest-available",
        action="store_true",
        help="Probe the FAA and print the newest in-force cycle that is served.",
    )
    args = parser.parse_args(argv)

    print(
        latest_available_cycle().isoformat()
        if args.latest_available
        else current_cycle().isoformat()
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
