import type {
  AdminOverview,
  ApiResult,
  CupData,
  CupMatch,
  CupQualification,
  CupQualificationEntry,
  DashboardData,
  Division,
  GameweekStatus,
  H2HFixture,
  H2HStanding,
  Highlight,
  HighlightKind,
  Manager,
  MatchDetail,
  MatchPlayerLine,
  MatchSideDetail,
  MatchStatus,
  PlayerState,
  ScoreBreakdown,
  SquadSlot,
  StandingEntry,
  Violation
} from "./types";
import { withZones } from "./zones";

export type ClassicPeriod = "season_1" | "season_2" | "full";

interface RuntimeConfiguration {
  apiUrl: string | undefined;
  adminApiKey: string | undefined;
  adminActor: string;
  seasonId: number;
  seasonLabel: string;
  h2hScheduleId: number;
}

interface ManagerResponse {
  id: number;
  fpl_entry_id: number;
  manager_name: string;
  team_name: string;
  division: Division;
  active_status: "active" | "suspended" | "removed" | "locked" | "deleted" | "pending_review";
  registration_status: "pending" | "confirmed" | "rejected";
  season_joined: string;
  season_2_league_joined: boolean;
  season_2_join_gameweek: number | null;
  created_at: string;
  updated_at: string;
}

interface ClassicStandingResponse {
  rank: number;
  manager_id: number;
  fpl_entry_id: number;
  manager_name: string;
  team_name: string;
  division: Division;
  gameweeks_scored: number;
  season_points: number;
  full_season_points: number;
  totw_count: number;
  highest_gameweek_score: number;
}

interface ClassicStandingsEnvelope {
  season_id: number;
  period: ClassicPeriod;
  division: Division;
  start_gameweek: number;
  end_gameweek: number;
  standings: ClassicStandingResponse[];
}

interface H2HStandingResponse {
  rank: number;
  manager_id: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  points_for: number;
  points_against: number;
  point_difference: number;
  h2h_table_points: number;
  full_net_fpl_points: number;
}

interface H2HMatchResponse {
  id: number;
  schedule_id: number;
  gameweek_number: number;
  home_manager_id: number;
  away_manager_id: number;
  home_score: number | null;
  away_score: number | null;
  winner_manager_id: number | null;
  status: MatchStatus;
  walkover_reason: string | null;
  is_playoff: boolean;
  bracket_position: string | null;
}

interface MatchupPlayerLineResponse {
  element_id: number;
  web_name: string | null;
  home_multiplier: number;
  away_multiplier: number;
  net_multiplier: number;
  points: number;
  swing_points: number;
  state: PlayerState;
  fixtures_total: number;
  fixtures_unresolved: number;
  is_home_captain: boolean;
  is_away_captain: boolean;
}

interface SquadSlotResponse {
  element_id: number;
  web_name: string | null;
  club: string | null;
  squad_position: number;
  element_type: number;
  multiplier: number;
  points: number;
  contribution_points: number;
  state: PlayerState;
  fixtures_total: number;
  fixtures_unresolved: number;
  is_starter: boolean;
  is_substitute_goalkeeper: boolean;
  bench_order: number | null;
  is_captain: boolean;
  is_vice_captain: boolean;
}

interface CupQualificationEntryResponse {
  rank: number;
  manager_id: number;
  manager_name: string;
  team_name: string;
  division: Division;
  qualification_points: number;
  gameweeks_counted: number;
  gameweeks_excluded: number[];
  totw_count: number;
  captain_points: number;
  enters_at_round: number | null;
}

interface CupQualificationResponse {
  season_id: number;
  season_half: number;
  start_gameweek: number;
  end_gameweek: number;
  is_settled: boolean;
  high: CupQualificationEntryResponse[];
  low: CupQualificationEntryResponse[];
}

interface MatchupChipPlayResponse {
  chip: string;
  gameweek: number;
  short: string;
}

interface MatchupChipsResponse {
  played_this_gameweek: MatchupChipPlayResponse | null;
  used: MatchupChipPlayResponse[];
  remaining: string[];
}

interface MatchupSideResponse {
  manager_id: number;
  fpl_entry_id: number;
  chips: MatchupChipsResponse;
  manager_name: string;
  team_name: string;
  score: number | null;
  gross_points: number | null;
  transfer_cost: number | null;
  bench_points: number | null;
  chip_used: string | null;
  captain_points: number | null;
  goals_counted: number | null;
  is_totw: boolean;
  remaining: {
    players_remaining: number;
    effective_players_remaining: number;
    fixtures_remaining: number;
  };
  squad: SquadSlotResponse[];
}

interface H2HMatchDetailResponse {
  match_id: number;
  gameweek_number: number;
  status: MatchStatus;
  score_state: "upcoming" | "live" | "provisional" | "final" | null;
  is_playoff: boolean;
  bracket_position: string | null;
  walkover_reason: string | null;
  home: MatchupSideResponse;
  away: MatchupSideResponse;
  shared: MatchupPlayerLineResponse[];
  differentials: MatchupPlayerLineResponse[];
  captain_differential: MatchupPlayerLineResponse[];
}

interface HighlightResponse {
  kind: HighlightKind;
  gameweek_number: number | null;
  manager_id: number;
  manager_name: string;
  team_name: string;
  value: number;
  is_provisional: boolean;
}

interface FPLStatusResponse {
  gameweek_number: number | null;
  gameweek_name: string | null;
  state: "preseason" | "upcoming" | "live" | "provisional" | "final";
  deadline: string | null;
  completed_fixtures: number;
  total_fixtures: number;
  observed_at: string;
}

interface CupCompetitionResponse {
  id: number;
  season_id: number;
  name: string;
  season_half: number;
  qualification_end_gameweek: number;
}

interface CupMatchResponse {
  id: number;
  cup_round_id: number;
  tie_id: string;
  slot_a_label: string;
  slot_b_label: string;
  manager_a_id: number | null;
  manager_b_id: number | null;
  manager_a_score: number | null;
  manager_b_score: number | null;
  winner_manager_id: number | null;
  status: MatchStatus;
  tie_break_step_used: string | null;
  random_draw_result: string | null;
  is_third_place_match: boolean;
}

interface CupRoundResponse {
  id: number;
  name: string;
  round_order: number;
  gameweek_number: number;
  has_third_place_match: boolean;
  matches: CupMatchResponse[];
}

interface CupBracketResponse {
  competition: CupCompetitionResponse;
  rounds: CupRoundResponse[];
}

interface ViolationResponse {
  id: number;
  manager_id: number;
  gameweek_number: number;
  violation_type: "transfer_hit" | "late_season_2_join" | "manual";
  detected_count: number;
  confirmed_count: number;
  status:
    | "detected"
    | "pending_review"
    | "approved_exception"
    | "confirmed"
    | "rejected"
    | "overridden";
  admin_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

interface RequestOptions {
  admin?: boolean;
  revalidate?: number;
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
}

export type ViolationReviewAction =
  | "request_forgotten_chip_review"
  | "approve_exception"
  | "reject_exception"
  | "confirm"
  | "override";

export class ApiConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigurationError";
  }
}

export class ApiRequestError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status?: number, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

function positiveInteger(
  value: string | undefined,
  {
    name,
    fallback,
    required
  }: {
    name: string;
    fallback: number;
    required: boolean;
  }
): number {
  if (!value?.trim()) {
    if (required) throw new ApiConfigurationError(`${name} is required in production.`);
    return fallback;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new ApiConfigurationError(`${name} must be a positive integer.`);
  }
  return parsed;
}

function runtimeConfiguration(): RuntimeConfiguration {
  const apiUrl = (process.env.VMF_API_URL ?? process.env.NEXT_PUBLIC_API_URL)
    ?.trim()
    .replace(/\/+$/, "");
  const requireIds = process.env.NODE_ENV === "production";

  return {
    apiUrl: apiUrl || undefined,
    adminApiKey: process.env.VMF_ADMIN_API_KEY?.trim() || undefined,
    adminActor: process.env.VMF_ADMIN_ACTOR?.trim() || "vmf-web",
    seasonId: positiveInteger(process.env.VMF_SEASON_ID, {
      name: "VMF_SEASON_ID",
      fallback: 1,
      required: requireIds
    }),
    seasonLabel: process.env.VMF_SEASON_LABEL?.trim() || "2026/27",
    h2hScheduleId: positiveInteger(process.env.VMF_H2H_SCHEDULE_ID, {
      name: "VMF_H2H_SCHEDULE_ID",
      fallback: 1,
      required: requireIds
    })
  };
}

function now(): string {
  return new Date().toISOString();
}

function result<T>(data: T, source: ApiResult<T>["source"], updatedAt = now()): ApiResult<T> {
  return { data, source, updatedAt };
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
  const configuration = runtimeConfiguration();
  if (!configuration.apiUrl) {
    throw new ApiConfigurationError(
      "VMF_API_URL (or NEXT_PUBLIC_API_URL) is missing, so live data cannot be loaded."
    );
  }

  const headers = new Headers({ Accept: "application/json" });
  if (options.admin) {
    if (!configuration.adminApiKey) {
      throw new ApiConfigurationError(
        "VMF_ADMIN_API_KEY is missing. The admin key must be a server-side variable on Vercel."
      );
    }
    headers.set("X-Admin-Key", configuration.adminApiKey);
    headers.set("X-Admin-Actor", configuration.adminActor);
  }
  if (options.body !== undefined) headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    const method = options.method ?? "GET";
    const bypassCache = options.admin || method !== "GET";
    response = await fetch(`${configuration.apiUrl}${path}`, {
      headers,
      method,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: bypassCache ? "no-store" : undefined,
      next: bypassCache ? undefined : { revalidate: options.revalidate ?? 60 },
      signal: AbortSignal.timeout(8_000)
    });
  } catch (error) {
    throw new ApiRequestError("The VMF API could not be reached.", undefined, { cause: error });
  }

  if (!response.ok) {
    throw new ApiRequestError(`The VMF API returned HTTP ${response.status}.`, response.status);
  }

  try {
    const data = (await response.json()) as T;
    return result(data, "live");
  } catch (error) {
    throw new ApiRequestError("The VMF API returned invalid JSON.", response.status, {
      cause: error
    });
  }
}

function toManager(raw: ManagerResponse): Manager {
  return {
    id: String(raw.id),
    fplEntryId: raw.fpl_entry_id,
    name: raw.manager_name,
    teamName: raw.team_name,
    division: raw.division,
    rank: null,
    gameweekPoints: null,
    totalPoints: null,
    totw: null,
    h2hPoints: null,
    violations: null,
    status: raw.active_status,
    joinedAt: raw.created_at
  };
}

function toStanding(raw: ClassicStandingResponse, period: ClassicPeriod): StandingEntry {
  return {
    rank: raw.rank,
    previousRank: null,
    managerId: String(raw.manager_id),
    fplEntryId: raw.fpl_entry_id,
    managerName: raw.manager_name,
    teamName: raw.team_name,
    division: raw.division,
    gameweekPoints: null,
    totalPoints: period === "full" ? raw.full_season_points : raw.season_points,
    totw: raw.totw_count,
    violations: null,
    form: []
  };
}

function managerLookup(rawManagers: ManagerResponse[]): Map<number, ManagerResponse> {
  return new Map(rawManagers.map((manager) => [manager.id, manager]));
}

function fixtureSide(
  managerId: number | null,
  score: number | null,
  managersById: Map<number, ManagerResponse>,
  winnerManagerId: number | null
): H2HFixture["home"] {
  const manager = managerId === null ? undefined : managersById.get(managerId);
  return {
    managerId: managerId === null ? "tbd" : String(managerId),
    managerName: manager?.manager_name ?? (managerId === null ? "TBD" : `Manager #${managerId}`),
    teamName: manager?.team_name ?? (managerId === null ? "TBD" : `Team #${managerId}`),
    // Carried through so the site can send a reader to this manager's own
    // Gameweek page on FPL, which is the source every score here comes from.
    fplEntryId: manager?.fpl_entry_id ?? null,
    score,
    isWinner: managerId !== null && managerId === winnerManagerId
  };
}

function toFixture(raw: H2HMatchResponse, managersById: Map<number, ManagerResponse>): H2HFixture {
  return {
    id: String(raw.id),
    gameweek: raw.gameweek_number,
    bracketLabel: raw.is_playoff ? (raw.bracket_position ?? "Play-off") : null,
    kickoff: null,
    status: raw.status,
    walkoverReason: raw.walkover_reason,
    home: fixtureSide(raw.home_manager_id, raw.home_score, managersById, raw.winner_manager_id),
    away: fixtureSide(raw.away_manager_id, raw.away_score, managersById, raw.winner_manager_id)
  };
}

function toH2HStanding(
  raw: H2HStandingResponse,
  managersById: Map<number, ManagerResponse>
): H2HStanding {
  const manager = managersById.get(raw.manager_id);
  const resultPoints = raw.wins * 3 + raw.draws;
  return {
    rank: raw.rank,
    managerId: String(raw.manager_id),
    managerName: manager?.manager_name ?? `Manager #${raw.manager_id}`,
    teamName: manager?.team_name ?? `Team #${raw.manager_id}`,
    played: raw.played,
    won: raw.wins,
    drawn: raw.draws,
    lost: raw.losses,
    pointsFor: raw.points_for,
    points: raw.h2h_table_points,
    deduction: Math.max(0, resultPoints - raw.h2h_table_points),
    form: []
  };
}

function tieBreakLabel(value: string | null, randomDrawResult: string | null): string | undefined {
  if (randomDrawResult) return `Administrator draw: ${randomDrawResult}`;
  if (!value) return undefined;
  const labels: Record<string, string> = {
    match_score: "Match score",
    walkover: "Walkover",
    totw_count: "Cumulative TotW",
    captain_points: "Captain points",
    goals: "Goals scored",
    fewer_cards: "Fewer cards",
    classic_points: "Classic points",
    admin_draw: "Administrator draw"
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function toCupMatch(raw: CupMatchResponse, managersById: Map<number, ManagerResponse>): CupMatch {
  return {
    id: String(raw.id),
    label: raw.tie_id,
    slotALabel: raw.slot_a_label,
    slotBLabel: raw.slot_b_label,
    status: raw.status,
    home: fixtureSide(raw.manager_a_id, raw.manager_a_score, managersById, raw.winner_manager_id),
    away: fixtureSide(raw.manager_b_id, raw.manager_b_score, managersById, raw.winner_manager_id),
    decidedBy: tieBreakLabel(raw.tie_break_step_used, raw.random_draw_result)
  };
}

/** GW1-GW13 for the first Cup, GW20-GW32 for the second. */
function qualificationWindow(half: 1 | 2): string {
  return half === 1 ? "GW1-GW13" : "GW20-GW32";
}

function emptyCup(half: 1 | 2): CupData {
  return {
    season: half,
    title: `VMF Cup · Season ${half}`,
    qualificationWindow: qualificationWindow(half),
    isDrawn: false,
    rounds: [],
    thirdPlace: null
  };
}

function cupFromBracket(
  half: 1 | 2,
  bracket: CupBracketResponse,
  managersById: Map<number, ManagerResponse>
): CupData {
  const rounds = bracket.rounds.map((round) => ({
    id: String(round.id),
    name: round.name,
    roundOrder: round.round_order,
    gameweek: round.gameweek_number,
    matches: round.matches
      .filter((match) => !match.is_third_place_match)
      .map((match) => toCupMatch(match, managersById))
  }));
  const thirdPlace = bracket.rounds
    .flatMap((round) => round.matches)
    .find((match) => match.is_third_place_match);

  return {
    season: half,
    title: bracket.competition.name,
    qualificationWindow: qualificationWindow(half),
    isDrawn: rounds.length > 0,
    rounds,
    thirdPlace: thirdPlace ? toCupMatch(thirdPlace, managersById) : null
  };
}

async function managersLive(): Promise<ApiResult<Manager[]>> {
  const response = await requestJson<ManagerResponse[]>("/managers");
  return result(
    response.data.filter((manager) => manager.registration_status === "confirmed").map(toManager),
    "live",
    response.updatedAt
  );
}

async function fplStatusLive(): Promise<ApiResult<FPLStatusResponse>> {
  const response = await requestJson<FPLStatusResponse>("/fpl/status");
  return result(response.data, "live", response.data.observed_at);
}

async function classicStandingsLive(
  division: Division,
  period: ClassicPeriod
): Promise<ApiResult<StandingEntry[]>> {
  const { seasonId } = runtimeConfiguration();
  const query = new URLSearchParams({
    season_id: String(seasonId),
    division,
    period
  });
  const response = await requestJson<ClassicStandingsEnvelope>(
    `/classic/standings?${query.toString()}`
  );
  return result(
    withZones(
      response.data.standings.map((entry) => toStanding(entry, response.data.period)),
      division
    ),
    "live",
    response.updatedAt
  );
}

async function h2hFixturesLive(gameweek?: number): Promise<ApiResult<H2HFixture[]>> {
  const { h2hScheduleId } = runtimeConfiguration();
  const query = new URLSearchParams({ schedule_id: String(h2hScheduleId) });
  if (gameweek !== undefined) query.set("gameweek", String(gameweek));
  const [matchesResponse, managersResponse] = await Promise.all([
    requestJson<H2HMatchResponse[]>(`/h2h/fixtures?${query.toString()}`),
    requestJson<ManagerResponse[]>("/managers")
  ]);
  const managersById = managerLookup(managersResponse.data);
  return result(
    matchesResponse.data.map((match) => toFixture(match, managersById)),
    "live",
    matchesResponse.updatedAt
  );
}

function toPlayerLine(raw: MatchupPlayerLineResponse): MatchPlayerLine {
  return {
    elementId: raw.element_id,
    name: raw.web_name ?? `#${raw.element_id}`,
    homeMultiplier: raw.home_multiplier,
    awayMultiplier: raw.away_multiplier,
    netMultiplier: raw.net_multiplier,
    points: raw.points,
    swingPoints: raw.swing_points,
    state: raw.state,
    fixturesTotal: raw.fixtures_total,
    fixturesUnresolved: raw.fixtures_unresolved,
    isHomeCaptain: raw.is_home_captain,
    isAwayCaptain: raw.is_away_captain
  };
}

function toSquadSlot(raw: SquadSlotResponse): SquadSlot {
  return {
    elementId: raw.element_id,
    name: raw.web_name ?? `#${raw.element_id}`,
    // An older API build has no club field at all, so absent and null are
    // both "no club", not a crash.
    club: raw.club ?? null,
    squadPosition: raw.squad_position,
    elementType: raw.element_type,
    multiplier: raw.multiplier,
    points: raw.points,
    contributionPoints: raw.contribution_points,
    state: raw.state,
    fixturesTotal: raw.fixtures_total,
    fixturesUnresolved: raw.fixtures_unresolved,
    isStarter: raw.is_starter,
    isSubstituteGoalkeeper: raw.is_substitute_goalkeeper,
    benchOrder: raw.bench_order,
    isCaptain: raw.is_captain,
    isViceCaptain: raw.is_vice_captain
  };
}

function toSideDetail(raw: MatchupSideResponse): MatchSideDetail {
  return {
    managerName: raw.manager_name,
    teamName: raw.team_name,
    score: raw.score,
    grossPoints: raw.gross_points,
    transferCost: raw.transfer_cost,
    benchPoints: raw.bench_points,
    chipUsed: raw.chip_used,
    chips: {
      playedThisGameweek: raw.chips?.played_this_gameweek ?? null,
      used: raw.chips?.used ?? [],
      remaining: raw.chips?.remaining ?? []
    },
    captainPoints: raw.captain_points,
    isTotw: raw.is_totw,
    remaining: {
      players: raw.remaining.players_remaining,
      effectivePlayers: raw.remaining.effective_players_remaining,
      fixtures: raw.remaining.fixtures_remaining
    },
    squad: (raw.squad ?? []).map(toSquadSlot)
  };
}

async function h2hMatchLive(id: string): Promise<ApiResult<MatchDetail>> {
  // One request for one match. Deriving this from the fixture list meant
  // fetching every match in the season to render a single page.
  const response = await requestJson<H2HMatchDetailResponse>(`/h2h/matches/${id}`);
  const raw = response.data;
  const breakdown: ScoreBreakdown[] = [];
  if (raw.home.gross_points !== null && raw.away.gross_points !== null) {
    breakdown.push({
      labelKey: "match.squadPoints",
      home: raw.home.gross_points,
      away: raw.away.gross_points
    });
  }
  if (raw.home.transfer_cost !== null && raw.away.transfer_cost !== null) {
    breakdown.push({
      labelKey: "match.transferCost",
      home: -raw.home.transfer_cost,
      away: -raw.away.transfer_cost
    });
  }
  if (raw.home.score !== null && raw.away.score !== null) {
    breakdown.push({ labelKey: "match.netPoints", home: raw.home.score, away: raw.away.score });
  }

  return result(
    {
      id: String(raw.match_id),
      gameweek: raw.gameweek_number,
      bracketLabel: raw.is_playoff ? (raw.bracket_position ?? "Play-off") : null,
      kickoff: null,
      status: raw.status,
      walkoverReason: raw.walkover_reason,
      home: {
        managerId: String(raw.home.manager_id),
        managerName: raw.home.manager_name,
        teamName: raw.home.team_name,
        fplEntryId: raw.home.fpl_entry_id || null,
        score: raw.home.score,
        isWinner:
          raw.home.score !== null && raw.away.score !== null
            ? raw.home.score > raw.away.score
            : false,
        activePlayers: raw.home.remaining.players_remaining
      },
      away: {
        managerId: String(raw.away.manager_id),
        managerName: raw.away.manager_name,
        teamName: raw.away.team_name,
        fplEntryId: raw.away.fpl_entry_id || null,
        score: raw.away.score,
        isWinner:
          raw.home.score !== null && raw.away.score !== null
            ? raw.away.score > raw.home.score
            : false,
        activePlayers: raw.away.remaining.players_remaining
      },
      scoreBreakdown: breakdown,
      events: [],
      homeDetail: toSideDetail(raw.home),
      awayDetail: toSideDetail(raw.away),
      shared: raw.shared.map(toPlayerLine),
      differentials: raw.differentials.map(toPlayerLine),
      ruleNote:
        raw.status === "walkover" && raw.walkover_reason
          ? { kind: "walkover", reason: raw.walkover_reason }
          : raw.score_state === "final"
            ? { kind: "settled" }
            : { kind: "provisional" }
    },
    "live",
    response.updatedAt
  );
}

const HIGHLIGHT_CATEGORY: Record<HighlightKind, Highlight["category"]> = {
  team_of_the_week: "totw",
  season_high: "record",
  captain_haul: "comeback",
  totw_leader: "record",
  bench_regret: "notice"
};

async function highlightsLive(): Promise<ApiResult<Highlight[]>> {
  const { seasonId } = runtimeConfiguration();
  const response = await requestJson<HighlightResponse[]>(`/highlights?season_id=${seasonId}`);
  return result(
    response.data.map((raw, index) => ({
      id: `${raw.kind}-${raw.manager_id}-${index}`,
      category: HIGHLIGHT_CATEGORY[raw.kind] ?? "notice",
      kind: raw.kind,
      managerName: raw.manager_name,
      teamName: raw.team_name,
      value: raw.value,
      gameweek: raw.gameweek_number,
      isProvisional: raw.is_provisional
    })),
    "live",
    response.updatedAt
  );
}

async function h2hStandingsLive(): Promise<ApiResult<H2HStanding[]>> {
  const { h2hScheduleId } = runtimeConfiguration();
  const [standingsResponse, managersResponse] = await Promise.all([
    requestJson<H2HStandingResponse[]>(`/h2h/standings?schedule_id=${h2hScheduleId}`),
    requestJson<ManagerResponse[]>("/managers")
  ]);
  const managersById = managerLookup(managersResponse.data);
  return result(
    standingsResponse.data.map((entry) => toH2HStanding(entry, managersById)),
    "live",
    standingsResponse.updatedAt
  );
}

/**
 * FPL's view of the current Gameweek in the app's own vocabulary.
 *
 * FPL calls the window between the deadline and the first kick-off "upcoming";
 * everywhere else in VMF that state is "open". Translating in one place keeps
 * every page agreeing on which Gameweek it is and whether it is running.
 */
function toGameweekStatus(fplStatus: FPLStatusResponse): GameweekStatus {
  return {
    number: fplStatus.gameweek_number ?? 0,
    name: fplStatus.gameweek_name ?? "Not started",
    state: fplStatus.state === "upcoming" ? "open" : fplStatus.state,
    deadline: fplStatus.deadline,
    progress:
      fplStatus.total_fixtures > 0
        ? Math.round((fplStatus.completed_fixtures / fplStatus.total_fixtures) * 100)
        : 0,
    fixturesComplete: fplStatus.completed_fixtures,
    fixturesTotal: fplStatus.total_fixtures
  };
}

async function gameweekLive(): Promise<ApiResult<GameweekStatus>> {
  const response = await fplStatusLive();
  return result(toGameweekStatus(response.data), response.source, response.updatedAt);
}

async function dashboardLive(): Promise<ApiResult<DashboardData>> {
  const configuration = runtimeConfiguration();
  const [managerResult, fplStatusResult] = await Promise.all([managersLive(), fplStatusLive()]);
  const fplStatus = fplStatusResult.data;
  const gameweek = fplStatus.gameweek_number ?? 0;
  const period: ClassicPeriod = gameweek >= 20 ? "season_2" : "season_1";
  const [highResult, lowResult, fixtureResult, h2hResult, highlightResult] = await Promise.all([
    classicStandingsLive("HIGH", period),
    classicStandingsLive("LOW", period),
    gameweek > 0 ? h2hFixturesLive(gameweek) : Promise.resolve(result([], "live")),
    // The reader's H2H position, which is a different competition from their
    // Classic division. A misconfigured schedule id must not take the whole
    // dashboard down with it, so this panel degrades on its own.
    h2hStandingsLive().catch(() => result<H2HStanding[]>([], "unavailable")),
    // A dashboard is worth showing without its stories, so a highlights
    // failure degrades that one panel rather than the whole page.
    highlightsLive().catch(() => result<Highlight[]>([], "unavailable"))
  ]);
  const currentFixtures = fixtureResult.data;
  const managerCount = (division: Division) =>
    managerResult.data.filter((manager) => manager.division === division).length;

  return result(
    {
      season: configuration.seasonLabel,
      gameweek: toGameweekStatus(fplStatus),
      metrics: [
        {
          labelKey: "metric.managers",
          value: String(managerResult.data.length),
          detailKey: "metric.managersDetail",
          tone: "blue"
        },
        {
          labelKey: "metric.divisionHigh",
          value: String(managerCount("HIGH")),
          detailKey: "metric.divisionDetail",
          tone: "lime"
        },
        {
          labelKey: "metric.divisionLow",
          value: String(managerCount("LOW")),
          detailKey: "metric.divisionDetail",
          tone: "coral"
        },
        {
          labelKey: "metric.h2hMatches",
          value: String(currentFixtures.length),
          detailKey: gameweek > 0 ? "metric.h2hScheduled" : "metric.h2hBeforeStart",
          detailVars: { gameweek },
          tone: "neutral"
        }
      ],
      fixtures: currentFixtures,
      managers: managerResult.data,
      standings: highResult.data.slice(0, 6),
      // Both divisions in full, so a reader can be found wherever they sit.
      // The preview above is the top six of HIGH; looking a manager up in
      // that would only ever find six of the forty-six.
      allStandings: [...highResult.data, ...lowResult.data],
      h2hStandings: h2hResult.data,
      recentHighlights: highlightResult.data.slice(0, 3)
    },
    "live",
    [managerResult, fplStatusResult, highResult, lowResult, fixtureResult]
      .map((item) => item.updatedAt)
      .sort()
      .at(-1)
  );
}

async function cupLive(half: 1 | 2): Promise<ApiResult<CupData>> {
  const { seasonId } = runtimeConfiguration();
  const [competitionsResponse, managersResponse] = await Promise.all([
    requestJson<CupCompetitionResponse[]>(`/cups?season_id=${seasonId}`),
    requestJson<ManagerResponse[]>("/managers")
  ]);
  const competition = competitionsResponse.data.find((item) => item.season_half === half);
  // A Cup that has not been drawn yet is a normal state for most of the
  // season, not a failure: the page says so rather than showing an error.
  if (!competition) return result(emptyCup(half), "live", competitionsResponse.updatedAt);

  const bracketResponse = await requestJson<CupBracketResponse>(`/cups/${competition.id}`);
  return result(
    cupFromBracket(half, bracketResponse.data, managerLookup(managersResponse.data)),
    "live",
    bracketResponse.updatedAt
  );
}

async function cupQualificationLive(half: 1 | 2): Promise<ApiResult<CupQualification>> {
  const { seasonId } = runtimeConfiguration();
  const response = await requestJson<CupQualificationResponse>(
    `/cups/qualification?season_id=${seasonId}&season_half=${half}`
  );
  const toEntry = (raw: CupQualificationEntryResponse): CupQualificationEntry => ({
    rank: raw.rank,
    managerId: String(raw.manager_id),
    managerName: raw.manager_name,
    teamName: raw.team_name,
    division: raw.division,
    points: raw.qualification_points,
    gameweeksCounted: raw.gameweeks_counted,
    gameweeksExcluded: raw.gameweeks_excluded,
    totw: raw.totw_count,
    entersAtRound: raw.enters_at_round
  });
  return result(
    {
      season: half,
      startGameweek: response.data.start_gameweek,
      endGameweek: response.data.end_gameweek,
      isSettled: response.data.is_settled,
      high: response.data.high.map(toEntry),
      low: response.data.low.map(toEntry)
    },
    "live",
    response.updatedAt
  );
}

async function adminViolationsLive(): Promise<ApiResult<Violation[]>> {
  const [violationResponse, managerResponse] = await Promise.all([
    requestJson<ViolationResponse[]>("/admin/violations", { admin: true }),
    requestJson<ManagerResponse[]>("/managers")
  ]);
  const managersById = managerLookup(managerResponse.data);
  const mapped = violationResponse.data.map((raw): Violation => {
    const manager = managersById.get(raw.manager_id);
    const effectiveCount =
      raw.status === "confirmed" || raw.status === "rejected" || raw.status === "overridden"
        ? raw.confirmed_count
        : raw.detected_count;
    const status: Violation["status"] =
      raw.status === "approved_exception" || (raw.status === "overridden" && effectiveCount === 0)
        ? "waived"
        : raw.status === "detected" || raw.status === "pending_review"
          ? "pending"
          : "confirmed";
    const severity = Math.min(3, Math.max(1, effectiveCount)) as 1 | 2 | 3;
    return {
      id: String(raw.id),
      managerId: String(raw.manager_id),
      managerName: manager?.manager_name ?? `Manager #${raw.manager_id}`,
      teamName: manager?.team_name ?? `Team #${raw.manager_id}`,
      division: manager?.division ?? "LOW",
      gameweek: raw.gameweek_number,
      reason: raw.admin_note ?? raw.violation_type.replaceAll("_", " "),
      transferCost: null,
      severity,
      occurrences: effectiveCount,
      sourceStatus: raw.status,
      status,
      impact: status === "waived" ? ["waived"] : ["threshold", "cupZero"],
      createdAt: raw.reviewed_at
    };
  });
  return result(mapped, "live", violationResponse.updatedAt);
}

export const vmfApi = {
  dashboard: dashboardLive,

  /** Which Gameweek it is and whether it is running, without the dashboard's cost. */
  gameweek: gameweekLive,

  classicStandings: (
    division: Division = "HIGH",
    period: ClassicPeriod = "season_1"
  ): Promise<ApiResult<StandingEntry[]>> => classicStandingsLive(division, period),

  h2hStandings: h2hStandingsLive,

  h2hFixtures: (gameweek?: number): Promise<ApiResult<H2HFixture[]>> => h2hFixturesLive(gameweek),

  h2hMatch: (id: string): Promise<ApiResult<MatchDetail>> => h2hMatchLive(id),

  cup: (season = 1): Promise<ApiResult<CupData>> => cupLive(season === 2 ? 2 : 1),

  cupQualification: (season = 1): Promise<ApiResult<CupQualification>> =>
    cupQualificationLive(season === 2 ? 2 : 1),

  highlights: highlightsLive,

  managers: managersLive,

  adminOverview: async (): Promise<ApiResult<AdminOverview>> => {
    const [managerResult, violationResult] = await Promise.all([
      managersLive(),
      adminViolationsLive()
    ]);
    return result(
      {
        sync: null,
        counts: {
          managers: managerResult.data.length,
          provisionalScores: null,
          pendingViolations: violationResult.data.filter((item) => item.status === "pending")
            .length,
          lockedTeams: managerResult.data.filter((item) => item.status === "locked").length
        },
        divisionAverages: [],
        recentJobs: []
      },
      "live",
      violationResult.updatedAt
    );
  },

  adminViolations: adminViolationsLive,

  reviewViolation: async (
    id: string,
    action: ViolationReviewAction,
    note: string,
    overriddenCount?: number
  ): Promise<void> => {
    await requestJson(`/admin/violations/${encodeURIComponent(id)}/review`, {
      admin: true,
      method: "POST",
      body: {
        action,
        note,
        ...(action === "override" ? { overridden_count: overriddenCount } : {})
      }
    });
  }
};

export const apiConfiguration = {
  get isConfigured(): boolean {
    return Boolean(runtimeConfiguration().apiUrl);
  },
  get baseUrl(): string | undefined {
    return runtimeConfiguration().apiUrl;
  }
};
