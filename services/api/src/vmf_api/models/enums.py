from enum import StrEnum


class Division(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class ManagerStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"
    LOCKED = "locked"
    DELETED = "deleted"
    PENDING_REVIEW = "pending_review"


class RegistrationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class SeasonStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class PhaseType(StrEnum):
    CLASSIC_SEASON_1 = "classic_season_1"
    CLASSIC_SEASON_2 = "classic_season_2"
    H2H_GROUP = "h2h_group"
    H2H_PLAYOFF = "h2h_playoff"
    CUP_SEASON_1 = "cup_season_1"
    CUP_SEASON_2 = "cup_season_2"


class ScoreState(StrEnum):
    UPCOMING = "upcoming"
    LIVE = "live"
    PROVISIONAL = "provisional"
    FINAL = "final"


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    PROVISIONAL = "provisional"
    FINAL = "final"
    WALKOVER = "walkover"


class ViolationType(StrEnum):
    TRANSFER_HIT = "transfer_hit"
    LATE_SEASON_2_JOIN = "late_season_2_join"
    MANUAL = "manual"


class DecisionType(StrEnum):
    VIOLATION_REVIEW = "violation_review"
    SCORE_OVERRIDE = "score_override"
    GAMEWEEK_REOPEN = "gameweek_reopen"
    GAMEWEEK_FINALIZE = "gameweek_finalize"
    MANAGER_STATUS = "manager_status"
    ADMIN_DRAW = "admin_draw"
