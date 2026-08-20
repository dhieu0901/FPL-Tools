import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiConfigurationError, vmfApi } from "./api";

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  vi.stubEnv("VMF_API_URL", "");
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("VMF API client", () => {
  it("refuses to load anything without an API URL", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    await expect(vmfApi.managers()).rejects.toBeInstanceOf(ApiConfigurationError);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("surfaces an API failure rather than inventing a standing", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api/");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ detail: "down" }, 503));

    await expect(vmfApi.managers()).rejects.toMatchObject({
      name: "ApiRequestError",
      status: 503
    });
  });

  it("calls the real managers route and maps the backend response", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api/");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: 7,
          fpl_entry_id: 12345,
          manager_name: "Nguyễn Văn A",
          team_name: "Hà Nội FC",
          division: "HIGH",
          active_status: "active",
          registration_status: "confirmed",
          season_joined: "2026/27",
          season_2_league_joined: false,
          season_2_join_gameweek: null,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z"
        }
      ])
    );

    const response = await vmfApi.managers();

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://api.example.test/api/managers",
      expect.any(Object)
    );
    expect(response).toMatchObject({
      source: "live",
      data: [
        {
          id: "7",
          name: "Nguyễn Văn A",
          teamName: "Hà Nội FC",
          division: "HIGH",
          totalPoints: null
        }
      ]
    });
  });

  it("sends every required Classic query parameter and maps its envelope", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api");
    vi.stubEnv("VMF_SEASON_ID", "9");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        season_id: 9,
        period: "season_2",
        division: "LOW",
        start_gameweek: 20,
        end_gameweek: 38,
        standings: [
          {
            rank: 1,
            manager_id: 12,
            manager_name: "Manager B",
            team_name: "Team B",
            division: "LOW",
            gameweeks_scored: 2,
            season_points: 150,
            full_season_points: 900,
            totw_count: 1,
            highest_gameweek_score: 80
          }
        ]
      })
    );

    const response = await vmfApi.classicStandings("LOW", "season_2");
    const calledUrl = String(fetchSpy.mock.calls[0]?.[0]);

    expect(calledUrl).toContain("/classic/standings?");
    expect(calledUrl).toContain("season_id=9");
    expect(calledUrl).toContain("division=LOW");
    expect(calledUrl).toContain("period=season_2");
    expect(response.data[0]).toMatchObject({
      managerId: "12",
      totalPoints: 150,
      gameweekPoints: null,
      totw: 1
    });
  });

  it("keeps the admin key server-side and sends the required admin headers", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api");
    vi.stubEnv("VMF_ADMIN_API_KEY", "test-admin-key");
    vi.stubEnv("VMF_ADMIN_ACTOR", "test-admin");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      return url.endsWith("/admin/violations") ? jsonResponse([]) : jsonResponse([]);
    });

    await vmfApi.adminViolations();

    const adminCall = fetchSpy.mock.calls.find(([input]) =>
      String(input).endsWith("/admin/violations")
    );
    const headers = adminCall?.[1]?.headers as Headers;
    expect(headers.get("X-Admin-Key")).toBe("test-admin-key");
    expect(headers.get("X-Admin-Actor")).toBe("test-admin");
  });

  it("posts an authenticated violation review with its required note", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api");
    vi.stubEnv("VMF_ADMIN_API_KEY", "test-admin-key");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        violation: {},
        audit: {}
      })
    );

    await vmfApi.reviewViolation("17", "confirm", "Checked against the FPL transfer log");

    const [url, options] = fetchSpy.mock.calls[0] ?? [];
    const headers = options?.headers as Headers | undefined;
    expect(String(url)).toBe("https://api.example.test/api/admin/violations/17/review");
    expect(options).toMatchObject({
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({
        action: "confirm",
        note: "Checked against the FPL transfer log"
      })
    });
    expect(headers?.get("X-Admin-Key")).toBe("test-admin-key");
  });

  it("treats an override to zero as waived instead of level one", async () => {
    vi.stubEnv("VMF_API_URL", "https://api.example.test/api");
    vi.stubEnv("VMF_ADMIN_API_KEY", "test-admin-key");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/admin/violations")) {
        return jsonResponse([
          {
            id: 4,
            manager_id: 9,
            gameweek_number: 2,
            violation_type: "transfer_hit",
            detected_count: 2,
            confirmed_count: 0,
            status: "overridden",
            admin_note: "The source data was wrong",
            reviewed_by: "admin",
            reviewed_at: "2026-08-20T00:00:00Z"
          }
        ]);
      }
      return jsonResponse([
        {
          id: 9,
          fpl_entry_id: 999,
          manager_name: "Manager C",
          team_name: "Team C",
          division: "HIGH",
          active_status: "active",
          registration_status: "confirmed",
          season_joined: "2026/27",
          season_2_league_joined: false,
          season_2_join_gameweek: null,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z"
        }
      ]);
    });

    const response = await vmfApi.adminViolations();

    expect(response.data[0]).toMatchObject({
      status: "waived",
      occurrences: 0,
      impact: ["waived"]
    });
  });
});
