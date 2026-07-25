"""AIRAC cycle arithmetic. Pure date maths — no network."""

from datetime import date

import pytest

from aeronav_db import cycle


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        # On an effective date, that cycle is the one in force.
        (date(2026, 7, 9), date(2026, 7, 9)),
        # Mid-cycle.
        (date(2026, 7, 25), date(2026, 7, 9)),
        # The day before the next cycle takes effect.
        (date(2026, 8, 5), date(2026, 7, 9)),
        # The day it does.
        (date(2026, 8, 6), date(2026, 8, 6)),
        # Before the anchor: floor division must still round backwards.
        (date(2026, 6, 12), date(2026, 6, 11)),
        (date(2026, 6, 10), date(2026, 5, 14)),
    ],
)
def test_current_cycle(today: date, expected: date) -> None:
    assert cycle.current_cycle(today) == expected


def test_cycles_are_28_days_apart() -> None:
    cycles = cycle.recent_cycles(5, date(2026, 7, 25))

    assert cycles[0] == date(2026, 7, 9)
    for newer, older in zip(cycles, cycles[1:], strict=False):
        assert (newer - older).days == cycle.AIRAC_DAYS


def test_recent_cycles_are_newest_first() -> None:
    cycles = cycle.recent_cycles(4, date(2026, 7, 25))

    assert cycles == sorted(cycles, reverse=True)


def test_next_cycle_follows_the_current_one() -> None:
    assert cycle.next_cycle(date(2026, 7, 25)) == date(2026, 8, 6)


def test_nasr_url_embeds_the_effective_date() -> None:
    url = cycle.nasr_url(date(2026, 8, 6))

    assert url.endswith("28DaySubscription_Effective_2026-08-06.zip")


def test_latest_available_falls_back_when_newest_is_not_served(monkeypatch) -> None:
    """A cycle in force but not yet mirrored must not fail the build."""
    served = {date(2026, 6, 11)}
    monkeypatch.setattr(
        cycle, "is_published", lambda candidate, **_: candidate in served
    )

    assert cycle.latest_available_cycle(date(2026, 7, 25)) == date(2026, 6, 11)


def test_latest_available_prefers_the_newest_served_cycle(monkeypatch) -> None:
    served = {date(2026, 7, 9), date(2026, 6, 11)}
    monkeypatch.setattr(
        cycle, "is_published", lambda candidate, **_: candidate in served
    )

    assert cycle.latest_available_cycle(date(2026, 7, 25)) == date(2026, 7, 9)


def test_latest_available_raises_when_nothing_is_served(monkeypatch) -> None:
    monkeypatch.setattr(cycle, "is_published", lambda candidate, **_: False)

    with pytest.raises(RuntimeError, match="no published NASR cycle"):
        cycle.latest_available_cycle(date(2026, 7, 25))
