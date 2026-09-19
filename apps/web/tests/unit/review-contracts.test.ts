import { describe, expect, it } from "vitest";

import {
  repositoryReviewSchema,
  reviewResultSchema,
  reviewStateSchema,
} from "@/lib/contracts/review";

const reviewId = "123e4567-e89b-42d3-a456-426614174000";

const result = {
  findings: [
    {
      category: "security" as const,
      severity: "high" as const,
      title: "Unsanitized input",
      description: "User input reaches a query.",
      file: "app/api/example.ts",
      line_start: 12,
      line_end: 14,
      evidence: "The input is interpolated directly.",
      recommendation: "Use a parameterized query.",
      confidence: 0.95,
    },
  ],
  approval_granted: false,
};

describe("reviewResultSchema", () => {
  it("accepts a complete review result", () => {
    expect(reviewResultSchema.parse(result)).toEqual(result);
  });

  it("rejects unknown fields and invalid confidence", () => {
    expect(
      reviewResultSchema.safeParse({ ...result, unexpected: true }).success,
    ).toBe(false);
    expect(
      reviewResultSchema.safeParse({
        ...result,
        findings: [{ ...result.findings[0], confidence: 1.01 }],
      }).success,
    ).toBe(false);
  });
});

describe("reviewStateSchema", () => {
  it.each([
    { reviewId, status: "running" },
    { reviewId, status: "finished", result },
    { reviewId, status: "failed", error: "Worker timed out" },
  ])("accepts the $status state", (state) => {
    expect(reviewStateSchema.safeParse(state).success).toBe(true);
  });

  it("enforces correct payload with each state", () => {
    expect(
      reviewStateSchema.safeParse({
        reviewId,
        status: "finished",
        error: "Missing result",
      }).success,
    ).toBe(false);
    expect(
      reviewStateSchema.safeParse({
        reviewId,
        status: "failed",
        error: "",
      }).success,
    ).toBe(false);
  });
});

describe("repositoryReviewSchema", () => {
  it("turns API date strings into Date objects", () => {
    const parsed = repositoryReviewSchema.parse({
      id: reviewId,
      repositoryId: "223e4567-e89b-42d3-a456-426614174000",
      pullRequestNumber: 17,
      status: "finished",
      result,
      error: null,
      startedAt: "2026-09-18T08:00:00.000Z",
      finishedAt: "2026-09-18T08:03:00.000Z",
      updatedAt: "2026-09-18T08:03:00.000Z",
      createdAt: "2026-09-18T08:00:00.000Z",
    });

    expect(parsed.startedAt).toEqual(new Date("2026-09-18T08:00:00.000Z"));
    expect(parsed.finishedAt).toEqual(new Date("2026-09-18T08:03:00.000Z"));
  });
});
