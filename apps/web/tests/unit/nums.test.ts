import { describe, expect, it } from "vitest";

import { getAsPositiveInteger } from "@/lib/nums";

describe("getAsPositiveInteger", () => {
  it.each([
    ["1", 1],
    ["42", 42],
    ["001", 1],
  ])("parses %s", (value, expected) => {
    expect(getAsPositiveInteger(value)).toBe(expected);
  });

  it.each(["0", "-1", "1.5", "abc", "", "Infinity"])("rejects %s", (value) => {
    expect(getAsPositiveInteger(value)).toBeNull();
  });

  it("uses a fallback only when the value is missing", () => {
    expect(getAsPositiveInteger(null, 25)).toBe(25);
    expect(getAsPositiveInteger("invalid", 25)).toBeNull();
  });
});
