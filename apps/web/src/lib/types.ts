export type Division = "HIGH" | "LOW";
export type DataSource = "live" | "mock";
export type MatchStatus = "scheduled" | "live" | "provisional" | "final";
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
  deadline: string;
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
  previousRank: number;
  managerId: string;
  managerName: string;
  teamName: string;
  division: Division;
  gameweekPoints: number;
  totalPoints: number;
  totw: number;
  violations: number;
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
  kickoff: string;
  status: MatchStatus;
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
  rank: number;
  gameweekPoints: number;
  totalPoints: number;
  totw: number;
  h2hPoints: number;
  violations: number;
  status: "active" | "locked" | "removed";
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
  transferCost: number;
  severity: ViolationSeverity;
  status: ViolationStatus;
  impact: string[];
  createdAt: string;
}

export interface DashboardData {
  season: string;
  gameweek: GameweekStatus;
  metrics: LeagueMetric[];
  featuredFixture: H2HFixture;
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
  };
  counts: {
    managers: number;
    provisionalScores: number;
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
