import { describe, expect, it } from "vitest";
import { initials, rankDelta } from "./format";

describe("rankDelta", () => {
  it("reports a climb", () => {
    expect(rankDelta(2, 5)).toEqual({ direction: "up", value: 3 });
  });

  it("reports no movement", () => {
    expect(rankDelta(4, 4)).toEqual({ direction: "same", value: 0 });
  });
});

describe("initials", () => {
  it("takes the last two parts of a name", () => {
    expect(initials("Nguyễn Minh Anh")).toBe("MA");
  });
});
