import {
  adminOverview,
  cupData,
  dashboardData,
  fixtures,
  h2hStandings,
  highlights,
  managers,
  matchDetail,
  standings,
  violations
} from "./mock-data";
import type {
  AdminOverview,
  ApiResult,
  CupData,
  DashboardData,
  H2HFixture,
  H2HStanding,
  Highlight,
  Manager,
  MatchDetail,
  StandingEntry,
  Violation
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

interface ApiEnvelope<T> {
  data: T;
  updatedAt?: string;
}

function isApiEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  return typeof value === "object" && value !== null && "data" in value;
}

async function request<T>(path: string, fallback: T): Promise<ApiResult<T>> {
  if (!API_URL) {
    return {
      data: fallback,
      source: "mock",
      updatedAt: new Date().toISOString()
    };
  }

  try {
    const response = await fetch(`${API_URL}${path}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(5_000)
    });

    if (!response.ok) {
      throw new Error(`API ${response.status}`);
    }

    const payload: unknown = await response.json();
    const data = isApiEnvelope<T>(payload) ? payload.data : (payload as T);
    const updatedAt = isApiEnvelope<T>(payload)
      ? (payload.updatedAt ?? new Date().toISOString())
      : new Date().toISOString();

    return { data, source: "live", updatedAt };
  } catch {
    return {
      data: fallback,
      source: "mock",
      updatedAt: new Date().toISOString()
    };
  }
}

export const vmfApi = {
  dashboard: (): Promise<ApiResult<DashboardData>> => request("/public/dashboard", dashboardData),
  classicStandings: (): Promise<ApiResult<StandingEntry[]>> =>
    request("/public/classic/standings", standings),
  h2hStandings: (): Promise<ApiResult<H2HStanding[]>> =>
    request("/public/h2h/standings", h2hStandings),
  h2hFixtures: (): Promise<ApiResult<H2HFixture[]>> => request("/public/h2h/fixtures", fixtures),
  h2hMatch: (id: string): Promise<ApiResult<MatchDetail>> =>
    request(`/public/h2h/matches/${encodeURIComponent(id)}`, {
      ...matchDetail,
      id
    }),
  cup: (season = 1): Promise<ApiResult<CupData>> =>
    request(`/public/cups/${season}`, {
      ...cupData,
      season: season === 2 ? 2 : 1,
      title: `VMF Cup · Season ${season === 2 ? 2 : 1}`,
      qualificationWindow:
        season === 2 ? "Xét điểm hợp lệ từ GW20–GW33" : "Xét điểm hợp lệ từ GW1–GW14"
    }),
  highlights: (): Promise<ApiResult<Highlight[]>> => request("/public/highlights", highlights),
  managers: (): Promise<ApiResult<Manager[]>> => request("/public/managers", managers),
  adminOverview: (): Promise<ApiResult<AdminOverview>> => request("/admin/overview", adminOverview),
  adminViolations: (): Promise<ApiResult<Violation[]>> => request("/admin/violations", violations)
};

export const apiConfiguration = {
  isConfigured: Boolean(API_URL),
  baseUrl: API_URL
};
