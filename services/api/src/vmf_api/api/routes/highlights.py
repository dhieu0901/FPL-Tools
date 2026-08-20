from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from vmf_api.api.deps import SessionDep
from vmf_api.services.highlights import DEFAULT_LIMIT, HighlightKind, HighlightsService

router = APIRouter(prefix="/highlights", tags=["highlights"])


class HighlightResponse(BaseModel):
    """A fact, not a sentence. The interface writes the prose around it."""

    kind: HighlightKind
    gameweek_number: int | None
    manager_id: int
    manager_name: str
    team_name: str
    value: int
    is_provisional: bool
    #: The player a story is about, where there is one.
    subject: str | None = None
    #: A second value the sentence needs: a squad size, or which chip.
    detail: str | None = None


@router.get("", response_model=list[HighlightResponse])
async def highlights(
    session: SessionDep,
    season_id: Annotated[int, Query(gt=0)],
    limit: Annotated[int, Query(ge=1, le=20)] = DEFAULT_LIMIT,
) -> list[HighlightResponse]:
    rows = await HighlightsService(session, season_id=season_id).latest(limit=limit)
    return [
        HighlightResponse(
            kind=row.kind,
            gameweek_number=row.gameweek_number,
            manager_id=row.manager_id,
            manager_name=row.manager_name,
            team_name=row.team_name,
            value=row.value,
            is_provisional=row.is_provisional,
            subject=row.subject,
            detail=row.detail,
        )
        for row in rows
    ]
