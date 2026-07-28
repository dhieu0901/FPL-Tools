import { describe, expect, it } from "vitest";
import { initials, rankDelta } from "./format";

describe("rankDelta", () => {
  it("nhận diện tăng hạng", () => {
    expect(rankDelta(2, 5)).toEqual({ direction: "up", value: 3 });
  });

  it("nhận diện không đổi", () => {
    expect(rankDelta(4, 4)).toEqual({ direction: "same", value: 0 });
  });
});

describe("initials", () => {
  it("lấy hai thành phần cuối của tên", () => {
    expect(initials("Nguyễn Minh Anh")).toBe("MA");
  });
});
