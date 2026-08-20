import type { MessageKey } from "@/lib/i18n";

export type Division = "HIGH" | "LOW";
export type DataSource = "live" | "unavailable";
export type MatchStatus = "scheduled" | "live" | "provisional" | "final" | "walkover";
export type ViolationStatus = "pending" | "confirmed" | "waived";
export type ViolationSeverity = 1 | 2 | 3;

export interface ApiResult<T> {
  data: T;
  source: DataSource;
  updatedAt: string;
}

export interface GameweekStatus {
  number: number;
  name: string;
  state: "preseason" | "open" | "live" | "provisional" | "final";
  deadline: string | null;
  progress: number;
  fixturesComplete: number;
  fixturesTotal: number;
}

export interface LeagueMetric {
  /**
   * A dictionary key, not a sentence. Copy lives in one place so a metric
   * cannot drift out of step with the rest of the interface.
   */
  labelKey: MessageKey;
  detailKey: MessageKey;
  detailVars?: Record<string, string | number>;
  value: string;
  tone: "lime" | "coral" | "blue" | "neutral";
}

export interface StandingEntry {
  rank: number;
  previousRank: number | null;
  managerId: string;
  /** FPL's own id, so a team name links through to their season there. */
  fplEntryId: number;
  managerName: string;
  teamName: string;
  division: Division;
  gameweekPoints: number | null;
  totalPoints: number;
  totw: number;
  violations: number | null;
  form: Array<"W" | "D" | "L">;
  /** Set only where the boundary is unambiguous; see lib/zones. */
  qualification?: "promotion" | "relegation";
}

export interface H2HStanding {
  rank: number;
  managerId: string;
  managerName: string;
  teamName: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  pointsFor: number;
  points: number;
  deduction: number;
  form: Array<"W" | "D" | "L">;
}

export interface FixtureSide {
  managerId: string;
  managerName: string;
  teamName: string;
  /** FPL's own id, used to link a team through to its Gameweek page there. */
  fplEntryId: number | null;
  score: number | null;
  captain?: string;
  activePlayers?: number;
  isWinner?: boolean;
}

export interface H2HFixture {
  id: string;
  gameweek: number;
  /** Bracket name supplied by the backend; null means the group stage. */
  bracketLabel: string | null;
  kickoff: string | null;
  status: MatchStatus;
  walkoverReason?: string | null;
  home: FixtureSide;
  away: FixtureSide;
}

export interface ScoreBreakdown {
  /** Dictionary key rather than a finished label. */
  labelKey:
    | "match.squadPoints"
    | "match.transferCost"
    | "match.adminAdjustment"
    | "match.netPoints";
  home: number;
  away: number;
}

/** Machine-readable result note; the page turns it into a sentence. */
export type MatchRuleNote =
  | { kind: "walkover"; reason: string }
  | { kind: "settled" }
  | { kind: "provisional" };

export type PlayerState = "upcoming" | "playing" | "finished";

/** One player as he appears across both squads. */
export interface MatchPlayerLine {
  elementId: number;
  name: string;
  homeMultiplier: number;
  awayMultiplier: number;
  /** Zero cancels out; the sign says which side the differential favours. */
  netMultiplier: number;
  points: number;
  /** Points this player has already moved the margin by. */
  swingPoints: number;
  state: PlayerState;
  fixturesTotal: number;
  fixturesUnresolved: number;
  isHomeCaptain: boolean;
  isAwayCaptain: boolean;
}

/** One squad member, in the order FPL lists them. */
export interface SquadSlot {
  elementId: number;
  name: string;
  /** FPL's own club code, as shown in the game: "EVE", "ARS", "NFO". */
  club: string | null;
  squadPosition: number;
  /** 1 keeper, 2 defender, 3 midfielder, 4 forward. */
  elementType: number;
  multiplier: number;
  points: number;
  contributionPoints: number;
  state: PlayerState;
  fixturesTotal: number;
  fixturesUnresolved: number;
  isStarter: boolean;
  isSubstituteGoalkeeper: boolean;
  benchOrder: number | null;
  isCaptain: boolean;
  isViceCaptain: boolean;
}

export interface SideRemaining {
  players: number;
  effectivePlayers: number;
  /** Reported separately so a Double Gameweek player is not read as two. */
  fixtures: number;
}

/** A chip and the Gameweek it was played in. */
export interface ChipPlay {
  /** FPL's code: "wildcard", "freehit", "bboost", "3xc". */
  chip: string;
  gameweek: number;
  /** How managers write it: "BB1" is a Bench Boost played in GW1. */
  short: string;
}

export interface ChipStatus {
  /** The chip played in the Gameweek being viewed, or null for none. */
  playedThisGameweek: ChipPlay | null;
  /** Every chip spent this half of the season, oldest first. */
  used: ChipPlay[];
  /** Codes only: an unplayed chip has no Gameweek yet. */
  remaining: string[];
}

export interface MatchSideDetail {
  managerName: string;
  teamName: string;
  score: number | null;
  grossPoints: number | null;
  transferCost: number | null;
  benchPoints: number | null;
  chipUsed: string | null;
  chips: ChipStatus;
  captainPoints: number | null;
  isTotw: boolean;
  remaining: SideRemaining;
  squad: SquadSlot[];
}

export interface MatchDetail extends H2HFixture {
  scoreBreakdown: ScoreBreakdown[];
  events: Array<{
    time: string;
    title: string;
    description: string;
    tone: "positive" | "negative" | "neutral";
  }>;
  ruleNote?: MatchRuleNote;
  homeDetail?: MatchSideDetail;
  awayDetail?: MatchSideDetail;
  shared: MatchPlayerLine[];
  differentials: MatchPlayerLine[];
}

export interface CupMatch {
  id: string;
  /** Position in the published bracket, for example "Q1-7" or "SF-2". */
  label: string;
  /** What the bracket sheet prints in each side before anyone qualifies. */
  slotALabel: string;
  slotBLabel: string;
  status: MatchStatus;
  home: FixtureSide;
  away: FixtureSide;
  decidedBy?: string;
}

export interface CupRound {
  id: string;
  name: string;
  roundOrder: number;
  gameweek: number;
  matches: CupMatch[];
}

export interface CupData {
  season: 1 | 2;
  title: string;
  qualificationWindow: string;
  /** False until the qualification Gameweek is finalized and the Cup is drawn. */
  isDrawn: boolean;
  rounds: CupRound[];
  thirdPlace: CupMatch | null;
}

export interface CupQualificationEntry {
  rank: number;
  managerId: string;
  managerName: string;
  teamName: string;
  division: Division;
  points: number;
  gameweeksCounted: number;
  /** Gameweeks a confirmed violation removed from the Cup total. */
  gameweeksExcluded: number[];
  totw: number;
  /** 1 or 2 for a qualifying round, 3 for a bye to the round of 16. */
  entersAtRound: number | null;
}

export interface CupQualification {
  season: 1 | 2;
  startGameweek: number;
  endGameweek: number;
  isSettled: boolean;
  high: CupQualificationEntry[];
  low: CupQualificationEntry[];
}

export type HighlightKind =
  | "team_of_the_week"
  | "season_high"
  | "captain_haul"
  | "totw_leader"
  | "bench_regret";

export interface Highlight {
  id: string;
  category: "totw" | "record" | "comeback" | "notice";
  /**
   * The fact, not the sentence. The API must not decide which language the
   * reader sees, so the page writes the prose from this and the numbers.
   */
  kind: HighlightKind;
  managerName: string;
  teamName: string;
  value: number;
  gameweek: number | null;
  isProvisional: boolean;
}

export interface Manager {
  id: string;
  /** FPL's own id, used to link through to their season on FPL. */
  fplEntryId: number;
  name: string;
  teamName: string;
  division: Division;
  rank: number | null;
  gameweekPoints: number | null;
  totalPoints: number | null;
  totw: number | null;
  h2hPoints: number | null;
  violations: number | null;
  status: "active" | "suspended" | "removed" | "locked" | "deleted" | "pending_review";
  joinedAt: string;
}

export type ViolationImpact =
  | "waived"
  | "threshold"
  | "cupZero"
  | "h2hDeduction"
  | "level2Warning"
  | "keepTransferHit";

export interface Violation {
  id: string;
  managerId: string;
  managerName: string;
  teamName: string;
  division: Division;
  gameweek: number;
  reason: string;
  transferCost: number | null;
  severity: ViolationSeverity;
  occurrences?: number;
  sourceStatus?:
    | "detected"
    | "pending_review"
    | "approved_exception"
    | "confirmed"
    | "rejected"
    | "overridden";
  status: ViolationStatus;
  impact: ViolationImpact[];
  createdAt: string | null;
}

export interface DashboardData {
  season: string;
  gameweek: GameweekStatus;
  metrics: LeagueMetric[];
  /** Every tie of the current Gameweek, so a reader can be shown their own. */
  fixtures: H2HFixture[];
  /** The roster, for the "which of these is you" picker. */
  managers: Manager[];
  /** The Classic preview: the top six of HIGH. */
  standings: StandingEntry[];
  /** Both divisions in full, for finding the reader's own row. */
  allStandings: StandingEntry[];
  recentHighlights: Highlight[];
}

export interface AdminOverview {
  sync: {
    state: "healthy" | "delayed" | "failed";
    lastSuccessfulAt: string;
    nextRunAt: string;
    latencySeconds: number;
  } | null;
  counts: {
    managers: number;
    provisionalScores: number | null;
    pendingViolations: number;
    lockedTeams: number;
  };
  divisionAverages: Array<{
    division: Division;
    gameweek: number;
    average: number;
    eligibleManagers: number;
  }>;
  recentJobs: Array<{
    id: string;
    name: string;
    status: "success" | "running" | "failed";
    startedAt: string;
    duration: string;
  }>;
}
