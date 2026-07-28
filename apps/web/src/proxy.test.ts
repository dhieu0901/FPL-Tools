import { describe, expect, it } from "vitest";
import { hasValidAdminCredentials } from "./proxy";

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
