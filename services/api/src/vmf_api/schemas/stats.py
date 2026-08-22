from pydantic import BaseModel


class CaptainPickResponse(BaseModel):
    """One player, and how many managers gave him the armband."""

    element_id: int
    web_name: str | None = None
    club: str | None = None
    count: int


class ChipUseResponse(BaseModel):
    chip: str
    #: Managers who played it in the Gameweek being reported.
    this_gameweek: int
    #: Managers who have played it at any point this season.
    this_season: int


class LeagueStatsResponse(BaseModel):
    """What the league did with a Gameweek, rather than how it scored."""

    gameweek_number: int
    #: "ALL", "HIGH" or "LOW".
    division: str
    managers: int
    #: Squads published so far. Shares are out of this, not out of the roster,
    #: because a manager whose picks FPL has not opened yet has no armband to
    #: count and must not be reported as having chosen nobody.
    squads_known: int
    captains: list[CaptainPickResponse]
    chips: list[ChipUseResponse]
