"""Check both brackets against the bracket sheet the organisers published.

These are transcription tests. If someone edits a pairing by hand, the failure
should name the tie rather than surface three months later as the wrong two
managers walking out for a quarter-final.
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from vmf_api.domain.cup_bracket import (
    BRACKETS,
    CUP_SEASON_1,
    CUP_SEASON_2,
    Bracket,
    Seed,
    Winner,
    bracket_for_half,
    eliminated_ranks,
)

ALL_BRACKETS = pytest.mark.parametrize(
    "bracket", [CUP_SEASON_1, CUP_SEASON_2], ids=["season_1", "season_2"]
)


@ALL_BRACKETS
def test_round_shape(bracket: Bracket) -> None:
    assert [len(round_.ties) for round_ in bracket.rounds] == [12, 12, 8, 4, 2, 1]
    assert [round_.round_order for round_ in bracket.rounds] == [1, 2, 3, 4, 5, 6]
    assert bracket.final_round.has_third_place_match is True
    assert sum(round_.has_third_place_match for round_ in bracket.rounds) == 1


@ALL_BRACKETS
def test_rounds_run_on_consecutive_gameweeks(bracket: Bracket) -> None:
    gameweeks = [round_.gameweek_number for round_ in bracket.rounds]
    assert gameweeks == list(range(gameweeks[0], gameweeks[0] + 6))
    # Qualification stops the Gameweek before the first tie is played.
    assert bracket.qualification_end_gameweek == gameweeks[0] - 1


def test_gameweeks_match_the_published_schedule() -> None:
    assert [r.gameweek_number for r in CUP_SEASON_1.rounds] == [14, 15, 16, 17, 18, 19]
    assert [r.gameweek_number for r in CUP_SEASON_2.rounds] == [33, 34, 35, 36, 37, 38]
    assert CUP_SEASON_1.qualification_end_gameweek == 13
    assert CUP_SEASON_2.qualification_end_gameweek == 32
    assert CUP_SEASON_1.qualification_start_gameweek == 1
    assert CUP_SEASON_2.qualification_start_gameweek == 20


@ALL_BRACKETS
def test_forty_managers_enter_each_from_one_place(bracket: Bracket) -> None:
    seeds = bracket.entry_seeds()
    assert len(seeds) == 40, "40 of the 46 managers enter the Cup"
    assert len(set(seeds)) == 40, "no manager may enter twice"

    high = sorted(seed.rank for seed in seeds if seed.division == "HIGH")
    low = sorted(seed.rank for seed in seeds if seed.division == "LOW")
    assert high == list(range(1, 19)), "HIGH 1-18 enter, 19-20 are out"
    assert low == list(range(1, 23)), "LOW 1-22 enter, 23-26 are out"


@ALL_BRACKETS
def test_entry_round_of_each_seed_group(bracket: Bracket) -> None:
    by_round = {
        round_.round_order: {slot for tie in round_.ties for slot in (tie.first, tie.second)}
        for round_ in bracket.rounds
    }

    def seeds_in(order: int) -> set[Seed]:
        return {slot for slot in by_round[order] if isinstance(slot, Seed)}

    assert seeds_in(1) == {Seed("HIGH", r) for r in range(11, 19)} | {
        Seed("LOW", r) for r in range(7, 23)
    }
    assert seeds_in(2) == {Seed("HIGH", r) for r in range(4, 11)} | {
        Seed("LOW", r) for r in range(2, 7)
    }
    assert seeds_in(3) == {Seed("HIGH", r) for r in (1, 2, 3)} | {Seed("LOW", 1)}
    for order in (4, 5, 6):
        assert seeds_in(order) == set(), "the knockout stage takes winners only"


@ALL_BRACKETS
def test_every_winner_slot_points_at_an_earlier_tie(bracket: Bracket) -> None:
    seen: set[str] = set()
    for round_ in bracket.rounds:
        referenced = [
            slot.tie
            for tie in round_.ties
            for slot in (tie.first, tie.second)
            if isinstance(slot, Winner)
        ]
        assert set(referenced) <= seen, f"{round_.name} references a tie not yet played"
        assert len(referenced) == len(set(referenced)), (
            f"{round_.name} sends one winner into two ties"
        )
        seen.update(tie.tie_id for tie in round_.ties)


@ALL_BRACKETS
def test_every_tie_feeds_the_next_round(bracket: Bracket) -> None:
    for earlier, later in pairwise(bracket.rounds):
        consumed = {
            slot.tie
            for tie in later.ties
            for slot in (tie.first, tie.second)
            if isinstance(slot, Winner)
        }
        assert consumed == {tie.tie_id for tie in earlier.ties}, (
            f"{earlier.name} winners do not all reach {later.name}"
        )


@ALL_BRACKETS
def test_tie_identifiers_are_unique(bracket: Bracket) -> None:
    ids = [tie.tie_id for round_ in bracket.rounds for tie in round_.ties]
    assert len(ids) == len(set(ids))


def test_the_two_seedings_genuinely_differ() -> None:
    first = [(str(t.first), str(t.second)) for t in CUP_SEASON_1.rounds[0].ties]
    second = [(str(t.first), str(t.second)) for t in CUP_SEASON_2.rounds[0].ties]
    assert first != second, "Season 2 reseeds; it is not a copy of Season 1"


def test_published_season_1_first_round_pairings() -> None:
    assert [(str(t.first), str(t.second)) for t in CUP_SEASON_1.rounds[0].ties] == [
        ("H11", "L22"),
        ("H12", "L21"),
        ("L7", "L20"),
        ("L8", "L19"),
        ("H13", "L18"),
        ("H14", "L17"),
        ("L9", "L16"),
        ("L10", "L15"),
        ("H15", "L14"),
        ("H16", "L13"),
        ("L11", "H18"),
        ("L12", "H17"),
    ]


def test_published_season_2_first_round_pairings() -> None:
    assert [(str(t.first), str(t.second)) for t in CUP_SEASON_2.rounds[0].ties] == [
        ("L7", "L22"),
        ("L8", "L21"),
        ("H11", "L20"),
        ("H12", "L19"),
        ("L9", "L18"),
        ("L10", "L17"),
        ("H13", "L16"),
        ("H14", "L15"),
        ("L11", "H18"),
        ("L12", "H17"),
        ("H15", "L14"),
        ("H16", "L13"),
    ]


def test_round_of_16_byes_differ_between_the_halves() -> None:
    def byes(bracket: Bracket) -> list[str]:
        return [
            str(slot)
            for tie in bracket.rounds[2].ties
            for slot in (tie.first, tie.second)
            if isinstance(slot, Seed)
        ]

    assert byes(CUP_SEASON_1) == ["L1", "H3", "H2", "H1"]
    assert byes(CUP_SEASON_2) == ["H3", "L1", "H2", "H1"]


def test_round_for_gameweek() -> None:
    assert CUP_SEASON_1.round_for_gameweek(16).name == "Round of 16"
    assert CUP_SEASON_2.round_for_gameweek(38).name == "Final"
    assert CUP_SEASON_1.round_for_gameweek(20) is None


def test_bracket_lookup() -> None:
    assert bracket_for_half(1) is CUP_SEASON_1
    assert bracket_for_half(2) is CUP_SEASON_2
    assert set(BRACKETS) == {1, 2}
    with pytest.raises(ValueError, match="season half must be 1 or 2"):
        bracket_for_half(3)


def test_eliminated_ranks_are_the_places_no_bracket_uses() -> None:
    assert list(eliminated_ranks("HIGH", 20)) == [19, 20]
    assert list(eliminated_ranks("LOW", 26)) == [23, 24, 25, 26]
    for bracket in (CUP_SEASON_1, CUP_SEASON_2):
        entered = bracket.entry_seeds()
        assert not [
            seed
            for seed in entered
            if seed.rank in eliminated_ranks(seed.division, 20 if seed.division == "HIGH" else 26)
        ]
