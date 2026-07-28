import pytest

from vmf_api.integrations.fpl_parsers import (
    SchemaQuarantineError,
    parse_bootstrap,
    parse_entry_history,
    parse_fixtures,
    parse_live,
    parse_picks,
)


def bootstrap_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "events": [
            {
                "id": 1,
                "name": "Gameweek 1",
                "deadline_time": "2026-08-21T17:30:00Z",
                "finished": False,
                "data_checked": False,
                "is_current": True,
            }
        ],
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS"}],
        "elements": [
            {
                "id": 10,
                "team": 1,
                "element_type": 3,
                "web_name": "Saka",
                "first_name": "Bukayo",
                "second_name": "Saka",
                "now_cost": 100,
                "status": "a",
            }
        ],
    }
    payload.update(overrides)
    return payload


def live_payload(explain: object, *, total_points: int = 9, minutes: int = 90) -> dict[str, object]:
    return {
        "elements": [
            {
                "id": 10,
                "stats": {"total_points": total_points, "minutes": minutes},
                "explain": explain,
            }
        ]
    }


def picks_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "active_chip": "bboost",
        "automatic_subs": [{"element_in": 12, "element_out": 11}],
        "entry_history": {
            "event": 1,
            "points": 72,
            "event_transfers": 3,
            "event_transfers_cost": 8,
            "points_on_bench": 5,
        },
        "picks": [
            {"element": 10, "position": 1, "multiplier": 2, "is_captain": True},
            {"element": 11, "position": 2, "multiplier": 0, "is_vice_captain": True},
            {"element": 12, "position": 12, "multiplier": 1},
        ],
    }
    payload.update(overrides)
    return payload


def test_bootstrap_normalizes_events_teams_and_players() -> None:
    parsed = parse_bootstrap(bootstrap_payload())

    assert parsed.events[0].number == 1
    assert parsed.events[0].deadline_time is not None
    assert parsed.events[0].is_current is True
    assert parsed.teams[0].short_name == "ARS"
    assert parsed.players[0].full_name == "Bukayo Saka"


def test_bootstrap_tolerates_unknown_fields() -> None:
    payload = bootstrap_payload()
    payload["new_collection"] = [{"anything": True}]
    assert parse_bootstrap(payload).players[0].element_id == 10


@pytest.mark.parametrize(
    "payload",
    [
        bootstrap_payload(elements=[]),
        bootstrap_payload(teams="not-a-list"),
        bootstrap_payload(elements=[{"team": 1, "element_type": 3, "web_name": "X"}]),
        bootstrap_payload(events=[{"id": 39, "name": "GW39"}]),
    ],
)
def test_bootstrap_quarantines_broken_identity(payload: dict[str, object]) -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_bootstrap(payload)


def test_fixtures_accept_a_postponed_fixture_without_an_event() -> None:
    parsed = parse_fixtures(
        [
            {"id": 1, "event": 5, "kickoff_time": "2026-09-12T14:00:00Z", "started": True},
            {"id": 2, "event": None, "kickoff_time": None},
        ]
    )

    assert parsed[0].gameweek_number == 5
    assert parsed[0].started is True
    assert parsed[1].gameweek_number is None
    assert parsed[1].kickoff_time is None
    assert parsed[1].finished is False


def test_fixtures_reject_duplicate_ids() -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_fixtures([{"id": 1}, {"id": 1}])


def test_live_keeps_double_gameweek_at_fixture_grain() -> None:
    parsed = parse_live(
        live_payload(
            [
                {
                    "fixture": 100,
                    "stats": [
                        {"identifier": "minutes", "value": 90, "points": 2},
                        {"identifier": "goals_scored", "value": 1, "points": 4},
                    ],
                },
                {
                    "fixture": 101,
                    "stats": [
                        {"identifier": "minutes", "value": 90, "points": 2},
                        {"identifier": "goals_scored", "value": 2, "points": 8},
                        {"identifier": "yellow_cards", "value": 1, "points": -1},
                    ],
                },
            ]
        )
    )

    assert [stat.fixture_fpl_id for stat in parsed.stats] == [100, 101]
    assert [stat.total_points for stat in parsed.stats] == [6, 9]
    assert sum(stat.goals_scored for stat in parsed.stats) == 3
    assert parsed.stats[1].yellow_cards == 1
    assert parsed.unresolved_element_ids == ()


def test_live_counts_unknown_identifier_points_without_inventing_columns() -> None:
    parsed = parse_live(
        live_payload(
            [
                {
                    "fixture": 100,
                    "stats": [
                        {"identifier": "minutes", "value": 90, "points": 2},
                        {"identifier": "brand_new_stat", "value": 3, "points": 5},
                    ],
                }
            ]
        )
    )

    assert parsed.stats[0].total_points == 7
    assert parsed.stats[0].goals_scored == 0


def test_live_flags_scoring_elements_without_a_fixture_breakdown() -> None:
    parsed = parse_live(live_payload([], total_points=6))

    assert parsed.stats == ()
    assert parsed.unresolved_element_ids == (10,)


def test_live_ignores_elements_that_did_not_play() -> None:
    parsed = parse_live(live_payload([], total_points=0, minutes=0))

    assert parsed.stats == ()
    assert parsed.unresolved_element_ids == ()


def test_live_quarantines_a_payload_without_total_points() -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_live({"elements": [{"id": 10, "stats": {"minutes": 90}}]})


def test_picks_expose_captain_chip_and_automatic_substitutions() -> None:
    parsed = parse_picks(picks_payload())

    assert parsed.active_chip == "bboost"
    assert parsed.transfer_cost == 8
    assert parsed.gross_points == 72
    captain = next(item for item in parsed.items if item.is_captain)
    assert (captain.element_id, captain.multiplier) == (10, 2)
    assert next(item for item in parsed.items if item.element_id == 12).auto_subbed_in is True
    assert next(item for item in parsed.items if item.element_id == 11).auto_subbed_out is True


@pytest.mark.parametrize(
    "payload",
    [
        picks_payload(picks=[{"element": 10, "position": 1, "multiplier": 2, "is_captain": True}]),
        picks_payload(
            picks=[
                {"element": 10, "position": 1, "multiplier": 2, "is_captain": True},
                {"element": 11, "position": 1, "multiplier": 1, "is_vice_captain": True},
            ]
        ),
        picks_payload(
            picks=[
                {"element": 10, "position": 1, "multiplier": 2, "is_captain": True},
                {"element": 11, "position": 2, "multiplier": 1, "is_captain": True},
                {"element": 12, "position": 3, "multiplier": 1, "is_vice_captain": True},
            ]
        ),
        picks_payload(entry_history={"event": 1, "points": 72}),
    ],
)
def test_picks_quarantine_broken_squad_invariants(payload: dict[str, object]) -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_picks(payload)


def test_entry_history_maps_points_and_transfer_cost() -> None:
    rows = parse_entry_history(
        {
            "current": [
                {
                    "event": 1,
                    "points": 72,
                    "total_points": 72,
                    "event_transfers": 0,
                    "event_transfers_cost": 4,
                    "points_on_bench": 6,
                    "value": 1005,
                    "bank": 5,
                    "rank": 123456,
                }
            ]
        }
    )

    assert rows[0].gross_points == 72
    assert rows[0].transfer_cost == 4
    assert rows[0].points_on_bench == 6
    assert rows[0].squad_value == 1005


def test_entry_history_quarantines_a_row_without_transfer_cost() -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_entry_history({"current": [{"event": 1, "points": 72}]})
