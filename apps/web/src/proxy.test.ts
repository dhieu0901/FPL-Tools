import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { hasValidAdminCredentials, proxy } from "./proxy";

describe("admin proxy credentials", () => {
  it("accepts the exact configured username and password", () => {
    const authorization = `Basic ${btoa("admin:correct horse battery staple")}`;

    expect(hasValidAdminCredentials(authorization, "admin", "correct horse battery staple")).toBe(
      true
    );
  });

  it("rejects missing, malformed, or incorrect credentials", () => {
    expect(hasValidAdminCredentials(null, "admin", "secret")).toBe(false);
    expect(hasValidAdminCredentials("Bearer token", "admin", "secret")).toBe(false);
    expect(hasValidAdminCredentials("Basic !!!", "admin", "secret")).toBe(false);
    expect(hasValidAdminCredentials(`Basic ${btoa("admin:wrong")}`, "admin", "secret")).toBe(false);
  });
});

describe("the sign-in dialog", () => {
  const withHeaders = (headers: Record<string, string>) => {
    const request = new Request("https://vmf-web.vercel.app/admin", { headers });
    return proxy(request as unknown as NextRequest);
  };

  beforeEach(() => {
    vi.stubEnv("VMF_ADMIN_UI_USER", "admin");
    vi.stubEnv("VMF_ADMIN_UI_PASSWORD", "a-password");
  });

  it("is raised for a real navigation", () => {
    const response = withHeaders({ "sec-fetch-mode": "navigate" });

    expect(response.status).toBe(401);
    expect(response.headers.get("www-authenticate")).toContain("Basic");
  });

  it.each([
    ["a speculative prefetch", { "sec-purpose": "prefetch;prerender" }],
    ["the older purpose header", { purpose: "prefetch" }],
    ["a router prefetch", { "next-router-prefetch": "1" }],
    ["an RSC request", { rsc: "1" }],
    ["a background fetch", { "sec-fetch-mode": "cors" }]
  ])("is withheld from %s, which nobody asked for", (_label, headers) => {
    const response = withHeaders(headers);

    // Still refused, but silently: the visitor is reading a public page.
    expect(response.status).toBe(401);
    expect(response.headers.get("www-authenticate")).toBeNull();
  });

  it("reports the admin area as unconfigured rather than refusing", () => {
    vi.stubEnv("VMF_ADMIN_UI_PASSWORD", "");

    expect(withHeaders({ "sec-fetch-mode": "navigate" }).status).toBe(503);
  });
});
