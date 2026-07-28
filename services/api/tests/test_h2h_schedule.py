import pytest

from vmf_api.domain.h2h_schedule import generate_round_robin_schedule


def test_40_manager_35_round_schedule_is_balanced_and_non_repeating() -> None:
    manager_ids = list(range(1, 41))
    schedule = generate_round_robin_schedule(manager_ids, rounds=35)

    assert len(schedule) == 35
    assert all(len(round_matches) == 20 for round_matches in schedule)

    seen_pairs: set[frozenset[int]] = set()
    appearances = {manager_id: 0 for manager_id in manager_ids}
    for gameweek, round_matches in enumerate(schedule, start=1):
        round_participants: set[int] = set()
        assert all(match.round_number == gameweek for match in round_matches)
        for match in round_matches:
            assert match.home_manager_id != match.away_manager_id
            pair = frozenset((match.home_manager_id, match.away_manager_id))
            assert pair not in seen_pairs
            seen_pairs.add(pair)
            round_participants.update(pair)
            appearances[match.home_manager_id] += 1
            appearances[match.away_manager_id] += 1
        assert round_participants == set(manager_ids)

    assert len(seen_pairs) == 35 * 20
    assert set(appearances.values()) == {35}


def test_schedule_can_start_at_a_later_gameweek() -> None:
    schedule = generate_round_robin_schedule([1, 2, 3, 4], rounds=2, start_gameweek=8)
    assert [round_matches[0].round_number for round_matches in schedule] == [8, 9]


@pytest.mark.parametrize("ids", [[1], [1, 2, 3], [1, 1, 2, 3]])
def test_schedule_rejects_invalid_participants(ids: list[int]) -> None:
    with pytest.raises(ValueError):
        generate_round_robin_schedule(ids, rounds=1)
