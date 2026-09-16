import { z } from "zod";

export const findingSchema = z
  .object({
    category: z.enum(["quality", "performance", "security"]),
    severity: z.enum(["critical", "high", "medium", "low"]),
    title: z.string(),
    description: z.string(),
    file: z.string(),
    line_start: z.number().int().nullable(),
    line_end: z.number().int().nullable(),
    evidence: z.string(),
    recommendation: z.string(),
    confidence: z.number().min(0).max(1),
  })
  .strict();

export const reviewResultSchema = z
  .object({
    findings: z.array(findingSchema),
    approval_granted: z.boolean(),
  })
  .strict();

export const reviewStateSchema = z.discriminatedUnion("status", [
  z
    .object({
      reviewId: z.uuid(),
      status: z.literal("running"),
    })
    .strict(),

  z
    .object({
      reviewId: z.uuid(),
      status: z.literal("finished"),
      result: reviewResultSchema,
    })
    .strict(),

  z
    .object({
      reviewId: z.uuid(),
      status: z.literal("failed"),
      error: z.string().min(1).max(2000),
    })
    .strict(),
]);

export type Finding = z.infer<typeof findingSchema>;
export type ReviewResult = z.infer<typeof reviewResultSchema>;
export type ReviewState = z.infer<typeof reviewStateSchema>;


export const reviewStatusSchema = z.enum([
  "scheduled",
  "running",
  "finished",
  "failed",
]);

const apiDateSchema = z.iso
  .datetime()
  .transform((value) => new Date(value));

export const repositoryReviewSchema = z
  .object({
    id: z.uuid(),
    pullRequestNumber: z.number().int(),
    status: reviewStatusSchema,
    result: reviewResultSchema.nullable(),
    error: z.string().nullable(),
    startedAt: apiDateSchema.nullable(),
    finishedAt: apiDateSchema.nullable(),
    createdAt: apiDateSchema,
  })
  .strict();

export const reviewsResponseSchema = z
  .object({
    reviews: z.array(repositoryReviewSchema),
  })
  .strict();

export const createReviewResponseSchema = z
  .object({
    review: repositoryReviewSchema,
  })
  .strict();

export type RepositoryReview = z.infer<typeof repositoryReviewSchema>;
export type ReviewsResponse = z.infer<typeof reviewsResponseSchema>;