"""Tolerant readers that turn FPL JSON into normalized source facts.

The parsers accept unknown fields, because FPL adds them between seasons, but
they are strict about identity and required invariants. A payload that cannot
be trusted raises :class:`SchemaQuarantineError` instead of being silently
coerced to zeros.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

CONTRACT_VERSION = "1.0.0-draft"
PARSER_VERSION = 1

MINIMUM_GAMEWEEK = 1
MAXIMUM_GAMEWEEK = 38


class SchemaQuarantineError(ValueError):
    """The payload is missing an identity field or breaks a hard invariant."""


@dataclass(frozen=True, slots=True)
class ParsedEvent:
    number: int
    name: str | None
    deadline_time: datetime | None
    finished: bool
    data_checked: bool
    is_current: bool
    is_next: bool
    is_previous: bool


@dataclass(frozen=True, slots=True)
class ParsedTeam:
    team_fpl_id: int
    name: str
    short_name: str


@dataclass(frozen=True, slots=True)
class ParsedPlayer:
    element_id: int
    web_name: str
    full_name: str
    team_fpl_id: int
    element_type: int
    status: str | None
    now_cost: int | None


@dataclass(frozen=True, slots=True)
class ParsedBootstrap:
    events: tuple[ParsedEvent, ...]
    teams: tuple[ParsedTeam, ...]
    players: tuple[ParsedPlayer, ...]


@dataclass(frozen=True, slots=True)
class ParsedFixture:
    fixture_fpl_id: int
    gameweek_number: int | None
    kickoff_time: datetime | None
    started: bool
    finished: bool
    finished_provisional: bool
    minutes: int
    team_h_fpl_id: int | None
    team_a_fpl_id: int | None
    team_h_score: int | None
    team_a_score: int | None


@dataclass(frozen=True, slots=True)
class ParsedPlayerFixtureStat:
    element_id: int
    fixture_fpl_id: int
    minutes: int
    total_points: int
    goals_scored: int
    assists: int
    yellow_cards: int
    red_cards: int
    bonus: int


@dataclass(frozen=True, slots=True)
class ParsedLive:
    stats: tuple[ParsedPlayerFixtureStat, ...]
    #: Elements that scored in the aggregate but have no usable per-fixture
    #: breakdown. Their points must not be invented at fixture grain.
    unresolved_element_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedPickItem:
    element_id: int
    squad_position: int
    multiplier: int
    is_captain: bool
    is_vice_captain: bool
    auto_subbed_in: bool = False
    auto_subbed_out: bool = False


@dataclass(frozen=True, slots=True)
class ParsedPicks:
    active_chip: str | None
    event_transfers: int
    transfer_cost: int
    gross_points: int | None
    points_on_bench: int | None
    items: tuple[ParsedPickItem, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class ParsedHistoryRow:
    gameweek_number: int
    gross_points: int
    total_points: int | None
    event_transfers: int
    transfer_cost: int
    points_on_bench: int
    squad_value: int | None
    bank: int | None


@dataclass(frozen=True, slots=True)
class ParsedEntry:
    entry_id: int
    manager_name: str | None
    team_name: str | None


@dataclass(frozen=True, slots=True)
class ParsedH2HMatch:
    """One tie from the draw FPL made for a head-to-head league.

    Only the pairing is taken. FPL also reports its own running scores, and
    reading those would let a mid-week fetch overwrite results this league
    computes to its own rulebook - transfer costs, penalties, walkovers and
    all. The Gameweek and the two entries are the parts FPL alone can decide.
    """

    fpl_match_id: int
    gameweek_number: int
    home_entry_id: int
    away_entry_id: int
    is_knockout: bool


def parse_bootstrap(payload: object) -> ParsedBootstrap:
    root = _object(payload, "bootstrap")
    events = tuple(_event(item) for item in _array(root, "events", "bootstrap"))
    teams = tuple(_team(item) for item in _array(root, "teams", "bootstrap"))
    players = tuple(_player(item) for item in _array(root, "elements", "bootstrap"))
    if not events or not teams or not players:
        raise SchemaQuarantineError("bootstrap must contain events, teams and elements")
    _reject_duplicates((event.number for event in events), label="event id")
    _reject_duplicates((team.team_fpl_id for team in teams), label="team id")
    _reject_duplicates((player.element_id for player in players), label="element id")
    return ParsedBootstrap(events=events, teams=teams, players=players)


def parse_fixtures(payload: object) -> tuple[ParsedFixture, ...]:
    if not isinstance(payload, list):
        raise SchemaQuarantineError("fixtures payload must be a list")
    fixtures = tuple(_fixture(item) for item in payload)
    _reject_duplicates((fixture.fixture_fpl_id for fixture in fixtures), label="fixture id")
    return fixtures


def parse_live(payload: object) -> ParsedLive:
    root = _object(payload, "live")
    stats: list[ParsedPlayerFixtureStat] = []
    unresolved: list[int] = []
    for entry in _array(root, "elements", "live"):
        element = _object(entry, "live element")
        element_id = _required_int(element.get("id"), "live element id")
        element_stats = _object(element.get("stats"), f"live element {element_id} stats")
        # ``total_points`` is the identity invariant for a live element: without
        # it the payload cannot be trusted for scoring at all.
        aggregate_points = _required_int(
            element_stats.get("total_points"),
            f"live element {element_id} total_points",
        )

        explain = element.get("explain")
        parsed_for_element = _explain_rows(element_id, explain)
        if parsed_for_element:
            stats.extend(parsed_for_element)
            continue
        if aggregate_points != 0 or _optional_int(element_stats.get("minutes")):
            # Points exist but FPL has not published the per-fixture breakdown.
            # Recording an invented fixture row here would corrupt DGW handling.
            unresolved.append(element_id)
    return ParsedLive(stats=tuple(stats), unresolved_element_ids=tuple(unresolved))


def parse_picks(payload: object) -> ParsedPicks:
    root = _object(payload, "picks")
    history = _object(root.get("entry_history"), "picks entry_history")
    raw_items = _array(root, "picks", "picks")
    if not raw_items:
        raise SchemaQuarantineError("picks payload contains no picks")

    subbed_in: set[int] = set()
    subbed_out: set[int] = set()
    automatic_subs = root.get("automatic_subs")
    if isinstance(automatic_subs, list):
        for entry in automatic_subs:
            substitution = _object(entry, "automatic_subs entry")
            subbed_in.add(_required_int(substitution.get("element_in"), "automatic sub element_in"))
            subbed_out.add(
                _required_int(substitution.get("element_out"), "automatic sub element_out")
            )

    items = tuple(_pick_item(item, subbed_in, subbed_out) for item in raw_items)
    _reject_duplicates((item.element_id for item in items), label="pick element")
    _reject_duplicates((item.squad_position for item in items), label="pick position")
    if sum(item.is_captain for item in items) != 1:
        raise SchemaQuarantineError("picks payload must contain exactly one captain")
    if sum(item.is_vice_captain for item in items) != 1:
        raise SchemaQuarantineError("picks payload must contain exactly one vice-captain")

    return ParsedPicks(
        active_chip=_optional_str(root.get("active_chip")),
        event_transfers=_optional_int(history.get("event_transfers")) or 0,
        transfer_cost=_required_int(
            history.get("event_transfers_cost"),
            "picks entry_history event_transfers_cost",
        ),
        gross_points=_optional_int(history.get("points")),
        points_on_bench=_optional_int(history.get("points_on_bench")),
        items=items,
    )


def parse_entry_history(payload: object) -> tuple[ParsedHistoryRow, ...]:
    root = _object(payload, "entry history")
    rows = tuple(_history_row(item) for item in _array(root, "current", "entry history"))
    _reject_duplicates((row.gameweek_number for row in rows), label="history event")
    return rows


def parse_entry(payload: object) -> ParsedEntry:
    root = _object(payload, "entry")
    first_name = _optional_str(root.get("player_first_name"))
    last_name = _optional_str(root.get("player_last_name"))
    manager_name = " ".join(part for part in (first_name, last_name) if part) or None
    return ParsedEntry(
        entry_id=_required_int(root.get("id"), "entry id"),
        manager_name=manager_name,
        team_name=_optional_str(root.get("name")),
    )


def parse_h2h_matches(payload: object) -> tuple[tuple[ParsedH2HMatch, ...], bool]:
    """One page of a head-to-head draw, and whether another page follows.

    A bye carries no opponent, so it is dropped rather than quarantined: an
    odd-sized league is a legitimate thing for FPL to produce, and it is not
    this parser's job to decide the league is malformed because of it.
    """

    root = _object(payload, "h2h matches")
    matches: list[ParsedH2HMatch] = []
    for item in _array(root, "results", "h2h matches"):
        match = _object(item, "h2h match")
        if _flag(match.get("is_bye")):
            continue
        home = _optional_int(match.get("entry_1_entry"))
        away = _optional_int(match.get("entry_2_entry"))
        if home is None or away is None:
            # An empty seat in a knockout round that has not been filled yet.
            continue
        if home == away:
            raise SchemaQuarantineError(f"h2h match {match.get('id')} pairs an entry with itself")
        matches.append(
            ParsedH2HMatch(
                fpl_match_id=_required_int(match.get("id"), "h2h match id"),
                gameweek_number=_gameweek(_required_int(match.get("event"), "h2h match event")),
                home_entry_id=home,
                away_entry_id=away,
                is_knockout=_flag(match.get("is_knockout")),
            )
        )
    return tuple(matches), _flag(root.get("has_next"))


def _event(value: object) -> ParsedEvent:
    event = _object(value, "bootstrap event")
    return ParsedEvent(
        number=_gameweek(_required_int(event.get("id"), "event id")),
        name=_optional_str(event.get("name")),
        deadline_time=_optional_datetime(event.get("deadline_time"), "event deadline_time"),
        finished=_flag(event.get("finished")),
        data_checked=_flag(event.get("data_checked")),
        is_current=_flag(event.get("is_current")),
        is_next=_flag(event.get("is_next")),
        is_previous=_flag(event.get("is_previous")),
    )


def _team(value: object) -> ParsedTeam:
    team = _object(value, "bootstrap team")
    team_id = _required_int(team.get("id"), "team id")
    name = _optional_str(team.get("name"))
    short_name = _optional_str(team.get("short_name"))
    if not name or not short_name:
        raise SchemaQuarantineError(f"team {team_id} is missing a name")
    return ParsedTeam(team_fpl_id=team_id, name=name, short_name=short_name)


def _player(value: object) -> ParsedPlayer:
    player = _object(value, "bootstrap element")
    element_id = _required_int(player.get("id"), "element id")
    web_name = _optional_str(player.get("web_name"))
    if not web_name:
        raise SchemaQuarantineError(f"element {element_id} is missing web_name")
    first_name = _optional_str(player.get("first_name")) or ""
    second_name = _optional_str(player.get("second_name")) or ""
    full_name = " ".join(part for part in (first_name, second_name) if part) or web_name
    return ParsedPlayer(
        element_id=element_id,
        web_name=web_name,
        full_name=full_name,
        team_fpl_id=_required_int(player.get("team"), f"element {element_id} team"),
        element_type=_required_int(player.get("element_type"), f"element {element_id} type"),
        status=_optional_str(player.get("status")),
        now_cost=_optional_int(player.get("now_cost")),
    )


def _fixture(value: object) -> ParsedFixture:
    fixture = _object(value, "fixture")
    fixture_id = _required_int(fixture.get("id"), "fixture id")
    event = fixture.get("event")
    return ParsedFixture(
        fixture_fpl_id=fixture_id,
        # A postponed fixture legitimately has no event until it is rescheduled.
        gameweek_number=None if event is None else _gameweek(_required_int(event, "fixture event")),
        kickoff_time=_optional_datetime(fixture.get("kickoff_time"), "fixture kickoff_time"),
        started=_flag(fixture.get("started")),
        finished=_flag(fixture.get("finished")),
        finished_provisional=_flag(fixture.get("finished_provisional")),
        minutes=_optional_int(fixture.get("minutes")) or 0,
        team_h_fpl_id=_optional_int(fixture.get("team_h")),
        team_a_fpl_id=_optional_int(fixture.get("team_a")),
        team_h_score=_optional_int(fixture.get("team_h_score")),
        team_a_score=_optional_int(fixture.get("team_a_score")),
    )


def _explain_rows(element_id: int, explain: object) -> list[ParsedPlayerFixtureStat]:
    if not isinstance(explain, list) or not explain:
        return []
    rows: list[ParsedPlayerFixtureStat] = []
    for block in explain:
        entry = _object(block, f"live element {element_id} explain entry")
        fixture_id = _optional_int(entry.get("fixture"))
        if fixture_id is None:
            # Without a fixture reference the row has no source grain.
            continue
        identifiers = _identifier_values(element_id, entry.get("stats"))
        rows.append(
            ParsedPlayerFixtureStat(
                element_id=element_id,
                fixture_fpl_id=fixture_id,
                minutes=identifiers.get("minutes", (0, 0))[0],
                total_points=sum(points for _, points in identifiers.values()),
                goals_scored=identifiers.get("goals_scored", (0, 0))[0],
                assists=identifiers.get("assists", (0, 0))[0],
                yellow_cards=identifiers.get("yellow_cards", (0, 0))[0],
                red_cards=identifiers.get("red_cards", (0, 0))[0],
                bonus=identifiers.get("bonus", (0, 0))[0],
            )
        )
    return rows


def _identifier_values(element_id: int, stats: object) -> dict[str, tuple[int, int]]:
    """Map ``identifier`` to ``(value, points)`` for one fixture block."""

    if not isinstance(stats, list):
        return {}
    values: dict[str, tuple[int, int]] = {}
    for item in stats:
        stat = _object(item, f"live element {element_id} stat")
        identifier = _optional_str(stat.get("identifier"))
        if identifier is None:
            continue
        # Unknown identifiers still contribute points; only the named ones are
        # promoted to their own column.
        values[identifier] = (
            _optional_int(stat.get("value")) or 0,
            _optional_int(stat.get("points")) or 0,
        )
    return values


def _pick_item(
    value: object,
    subbed_in: set[int],
    subbed_out: set[int],
) -> ParsedPickItem:
    pick = _object(value, "pick")
    element_id = _required_int(pick.get("element"), "pick element")
    return ParsedPickItem(
        element_id=element_id,
        squad_position=_required_int(pick.get("position"), f"pick {element_id} position"),
        multiplier=_required_int(pick.get("multiplier"), f"pick {element_id} multiplier"),
        is_captain=_flag(pick.get("is_captain")),
        is_vice_captain=_flag(pick.get("is_vice_captain")),
        auto_subbed_in=element_id in subbed_in,
        auto_subbed_out=element_id in subbed_out,
    )


def _history_row(value: object) -> ParsedHistoryRow:
    row = _object(value, "entry history row")
    gameweek = _gameweek(_required_int(row.get("event"), "history event"))
    return ParsedHistoryRow(
        gameweek_number=gameweek,
        gross_points=_required_int(row.get("points"), f"history GW{gameweek} points"),
        total_points=_optional_int(row.get("total_points")),
        event_transfers=_optional_int(row.get("event_transfers")) or 0,
        transfer_cost=_required_int(
            row.get("event_transfers_cost"),
            f"history GW{gameweek} event_transfers_cost",
        ),
        points_on_bench=_optional_int(row.get("points_on_bench")) or 0,
        squad_value=_optional_int(row.get("value")),
        bank=_optional_int(row.get("bank")),
    )


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaQuarantineError(f"{label} payload must be an object")
    return value


def _array(payload: dict[str, Any], key: str, label: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise SchemaQuarantineError(f"{label} payload must contain a {key} list")
    return value


def _required_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaQuarantineError(f"{label} must be an integer")
    return value


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _flag(value: object) -> bool:
    return value is True


def _optional_datetime(value: object, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SchemaQuarantineError(f"{label} must be an ISO timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SchemaQuarantineError(f"{label} must be an ISO timestamp or null") from error
    if parsed.tzinfo is None:
        raise SchemaQuarantineError(f"{label} must include a timezone")
    return parsed


def _gameweek(value: int) -> int:
    if not MINIMUM_GAMEWEEK <= value <= MAXIMUM_GAMEWEEK:
        raise SchemaQuarantineError(
            f"gameweek {value} is outside {MINIMUM_GAMEWEEK}..{MAXIMUM_GAMEWEEK}"
        )
    return value


def _reject_duplicates(values: object, *, label: str) -> None:
    seen: set[object] = set()
    for value in values:  # type: ignore[union-attr]
        if value in seen:
            raise SchemaQuarantineError(f"duplicate {label}: {value}")
        seen.add(value)
