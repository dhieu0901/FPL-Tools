export type Division = "HIGH" | "LOW";
export type DataSource = "live" | "mock" | "unavailable";
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
  label: string;
  value: string;
  detail: string;
  tone: "lime" | "coral" | "blue" | "neutral";
}

export interface StandingEntry {
  rank: number;
  previousRank: number | null;
  managerId: string;
  managerName: string;
  teamName: string;
  division: Division;
  gameweekPoints: number | null;
  totalPoints: number;
  totw: number;
  violations: number | null;
  form: Array<"W" | "D" | "L">;
  qualification?: "title" | "championship" | "cup" | "playoff" | "safe" | "relegation";
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
  score: number | null;
  liveScore?: number;
  captain?: string;
  activePlayers?: number;
  isWinner?: boolean;
  isReplacement?: boolean;
}

export interface H2HFixture {
  id: string;
  gameweek: number;
  group: string;
  kickoff: string | null;
  status: MatchStatus;
  walkoverReason?: string | null;
  home: FixtureSide;
  away: FixtureSide;
}

export interface ScoreBreakdown {
  label: string;
  home: number;
  away: number;
}

export interface MatchDetail extends H2HFixture {
  scoreBreakdown: ScoreBreakdown[];
  events: Array<{
    time: string;
    title: string;
    description: string;
    tone: "positive" | "negative" | "neutral";
  }>;
  ruleNote?: string;
}

export interface CupMatch {
  id: string;
  label: string;
  status: MatchStatus;
  home: FixtureSide;
  away: FixtureSide;
  decidedBy?: string;
}

export interface CupRound {
  id: string;
  name: string;
  gameweek: string;
  matches: CupMatch[];
}

export interface CupData {
  season: 1 | 2;
  title: string;
  qualificationWindow: string;
  rounds: CupRound[];
  thirdPlace: CupMatch | null;
}

export interface Highlight {
  id: string;
  category: "totw" | "record" | "comeback" | "notice";
  eyebrow: string;
  title: string;
  description: string;
  value?: string;
  managerName?: string;
  gameweek: number;
}

export interface Manager {
  id: string;
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
  impact: string[];
  createdAt: string | null;
}

export interface DashboardData {
  season: string;
  gameweek: GameweekStatus;
  metrics: LeagueMetric[];
  featuredFixture: H2HFixture | null;
  standings: StandingEntry[];
  recentHighlights: Highlight[];
  notices: Array<{
    id: string;
    title: string;
    body: string;
    publishedAt: string;
    priority: "normal" | "important";
  }>;
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
