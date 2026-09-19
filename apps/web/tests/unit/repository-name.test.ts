import { describe, expect, it } from "vitest";

import { isRepositoryName, normalizeRepository } from "@/lib/repository-name";

describe("normalizeRepository", () => {
  it.each([
    [" owner/repository ", "owner/repository"],
    ["https://github.com/owner/repository", "owner/repository"],
    ["HTTP://GITHUB.COM/owner/repository.git", "owner/repository"],
    ["/owner/repository/", "owner/repository"],
  ])("normalizes %s", (input, expected) => {
    expect(normalizeRepository(input)).toBe(expected);
  });
});

describe("isRepositoryName", () => {
  it.each(["owner/repository", "open-ai/rewy.js", "a/b"])(
    "accepts %s",
    (repository) => {
      expect(isRepositoryName(repository)).toBe(true);
    },
  );

  it.each([
    "",
    "repo",
    "/repository",
    "owner/",
    "/",
    "owner/repository/extra",
    " owner/repository",
    "owner/repository ",
    "owner name/repository",
    "owner/repository name",
  ])("rejects %s", (repository) => {
    expect(isRepositoryName(repository)).toBe(false);
  });
});
