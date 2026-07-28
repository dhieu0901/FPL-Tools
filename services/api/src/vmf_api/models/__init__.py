"""ORM model registry.

Importing this module registers every table on ``Base.metadata`` for Alembic.
"""

from vmf_api.models.competition import CompetitionPhase, DivisionMembership, Gameweek, Season
from vmf_api.models.cup import CupCompetition, CupMatch, CupRound
from vmf_api.models.governance import AdminDecision, Violation, ViolationThresholdAction
from vmf_api.models.h2h import H2HMatch, H2HPenalty, H2HSchedule
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    FplTeam,
    ManagerGameweekHistory,
    ManagerPickItem,
    ManagerPickSnapshot,
    RawFplResponse,
    SyncRun,
)
from vmf_api.models.manager import Manager, ManagerExternalProfile
from vmf_api.models.scoring import ManagerGameweekScore

__all__ = [
    "AdminDecision",
    "CompetitionPhase",
    "CupCompetition",
    "CupMatch",
    "CupRound",
    "DivisionMembership",
    "FplFixture",
    "FplPlayer",
    "FplPlayerFixtureStat",
    "FplTeam",
    "Gameweek",
    "H2HMatch",
    "H2HPenalty",
    "H2HSchedule",
    "Manager",
    "ManagerExternalProfile",
    "ManagerGameweekHistory",
    "ManagerGameweekScore",
    "ManagerPickItem",
    "ManagerPickSnapshot",
    "RawFplResponse",
    "Season",
    "SyncRun",
    "Violation",
    "ViolationThresholdAction",
]
