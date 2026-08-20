import { describe, expect, it } from "vitest";
import type { StandingEntry } from "./types";
import { withZones } from "./zones";

function table(ranks: number[]): StandingEntry[] {
  return ranks.map((rank, index) => ({
    rank,
    previousRank: null,
    managerId: String(index + 1),
    managerName: `Manager ${index + 1}`,
    teamName: `Team ${index + 1}`,
    division: "HIGH",
    gameweekPoints: null,
    totalPoints: 100 - index,
    totw: 0,
    violations: null,
    form: []
  }));
}

const straight = (count: number) => table(Array.from({ length: count }, (_, i) => i + 1));

function zones(entries: StandingEntry[]): Array<string | undefined> {
  return entries.map((entry) => entry.qualification);
}

describe("withZones", () => {
  it("marks the top six of LOW for promotion", () => {
    const marked = withZones(straight(26), "LOW");

    expect(zones(marked).slice(0, 6)).toEqual(Array(6).fill("promotion"));
    expect(zones(marked).slice(6)).toEqual(Array(20).fill(undefined));
  });

  it("marks the bottom six of HIGH for relegation", () => {
    const marked = withZones(straight(20), "HIGH");

    expect(zones(marked).slice(0, 14)).toEqual(Array(14).fill(undefined));
    expect(zones(marked).slice(14)).toEqual(Array(6).fill("relegation"));
  });

  it("keeps both divisions the size they started at", () => {
    const up = withZones(straight(26), "LOW").filter((e) => e.qualification).length;
    const down = withZones(straight(20), "HIGH").filter((e) => e.qualification).length;

    expect(up).toBe(down);
  });

  it("shows nothing when the promotion boundary is shared", () => {
    // Two managers hold rank 6, so the sixth place up is not decided here.
    const shared = table([1, 2, 3, 4, 5, 6, 6, ...Array.from({ length: 19 }, (_, i) => i + 8)]);

    expect(zones(withZones(shared, "LOW")).every((zone) => zone === undefined)).toBe(true);
  });

  it("shows nothing when the relegation boundary is shared", () => {
    const shared = table([
      ...Array.from({ length: 13 }, (_, i) => i + 1),
      14,
      14,
      16,
      17,
      18,
      19,
      20
    ]);

    expect(zones(withZones(shared, "HIGH")).every((zone) => zone === undefined)).toBe(true);
  });

  it("ignores a tie clear of the boundary", () => {
    const tied = table([1, 2, 2, 4, ...Array.from({ length: 16 }, (_, i) => i + 5)]);

    expect(zones(withZones(tied, "HIGH")).filter(Boolean)).toHaveLength(6);
  });

  it("leaves a table too small to relegate from alone", () => {
    expect(zones(withZones(straight(6), "HIGH")).every((zone) => zone === undefined)).toBe(true);
    expect(zones(withZones(straight(3), "LOW")).every((zone) => zone === undefined)).toBe(true);
  });

  it("does not mutate the entries it was given", () => {
    const original = straight(26);
    withZones(original, "LOW");

    expect(original.every((entry) => entry.qualification === undefined)).toBe(true);
  });
});
