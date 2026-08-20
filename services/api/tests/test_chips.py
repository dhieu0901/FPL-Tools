"""Chip accounting: what has been spent, and what is left this half."""

from __future__ import annotations

import pytest

from vmf_api.domain.chips import (
    CHIPS_PER_HALF,
    abbreviation,
    chip_status,
    display_name,
    half_range,
    season_half,
    short_form,
)


def test_the_halves_follow_the_two_vmf_seasons() -> None:
    assert season_half(1) == 1
    assert season_half(19) == 1
    assert season_half(20) == 2
    assert season_half(38) == 2
    assert list(half_range(1)) == list(range(1, 20))
    assert list(half_range(2)) == list(range(20, 39))


def test_an_invalid_gameweek_or_half_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        season_half(0)
    with pytest.raises(ValueError, match="season half must be 1 or 2"):
        half_range(3)


def test_a_manager_who_has_played_nothing_holds_everything() -> None:
    status = chip_status(gameweek_number=5, used_by_gameweek={1: None, 2: None})

    assert status.played_this_gameweek is None
    assert status.used == ()
    assert status.remaining == CHIPS_PER_HALF


def test_a_chip_played_this_gameweek_is_reported_and_counted_as_spent() -> None:
    status = chip_status(gameweek_number=6, used_by_gameweek={6: "wildcard"})

    assert status.played_this_gameweek is not None
    assert status.played_this_gameweek.short == "WC6"
    assert [play.short for play in status.used] == ["WC6"]
    assert "wildcard" not in status.remaining
    assert len(status.remaining) == 3


def test_a_chip_played_earlier_stays_spent() -> None:
    status = chip_status(gameweek_number=12, used_by_gameweek={3: "bboost", 8: "3xc"})

    assert status.played_this_gameweek is None
    assert [play.short for play in status.used] == ["BB3", "TC8"]
    assert status.remaining == ("wildcard", "freehit")


def test_a_manager_can_run_out() -> None:
    used = {2: "wildcard", 4: "freehit", 6: "bboost", 8: "3xc"}
    status = chip_status(gameweek_number=10, used_by_gameweek=used)

    assert status.remaining == ()
    assert [play.short for play in status.used] == ["WC2", "FH4", "BB6", "TC8"]


def test_the_second_half_starts_from_a_full_set() -> None:
    """A Wildcard spent in GW6 is not held against Season 2."""

    used = {2: "wildcard", 6: "bboost", 21: "freehit"}
    status = chip_status(gameweek_number=24, used_by_gameweek=used)

    assert [play.short for play in status.used] == ["FH21"]
    assert status.remaining == ("wildcard", "bboost", "3xc")


def test_a_later_gameweek_does_not_leak_backwards() -> None:
    """Viewing GW5 must not reveal a chip played in GW9."""

    status = chip_status(gameweek_number=5, used_by_gameweek={9: "wildcard"})

    assert status.used == ()
    assert status.remaining == CHIPS_PER_HALF


def test_the_same_chip_reported_twice_is_still_one_chip() -> None:
    status = chip_status(gameweek_number=9, used_by_gameweek={4: "wildcard", 7: "wildcard"})

    # The earliest Gameweek is the one it was played in.
    assert [play.short for play in status.used] == ["WC4"]
    assert len(status.remaining) == 3


def test_remaining_keeps_the_order_fpl_issues_them() -> None:
    status = chip_status(gameweek_number=9, used_by_gameweek={4: "bboost"})

    assert status.remaining == ("wildcard", "freehit", "3xc")


def test_used_is_ordered_by_when_each_chip_was_played() -> None:
    status = chip_status(gameweek_number=12, used_by_gameweek={9: "3xc", 2: "bboost"})

    assert [play.short for play in status.used] == ["BB2", "TC9"]


def test_short_forms_are_the_ones_managers_write() -> None:
    assert short_form("bboost", 1) == "BB1"
    assert short_form("freehit", 1) == "FH1"
    assert short_form("wildcard", 1) == "WC1"
    assert short_form("3xc", 1) == "TC1"
    assert short_form("bboost", 27) == "BB27"
    # An unknown chip still produces something readable.
    assert abbreviation("assistant") == "ASSISTANT"


def test_display_names() -> None:
    assert display_name("bboost") == "Bench Boost"
    assert display_name("3xc") == "Triple Captain"
    assert display_name(None) is None
    # An unknown code is shown as FPL sent it rather than silently dropped.
    assert display_name("manager") == "manager"
