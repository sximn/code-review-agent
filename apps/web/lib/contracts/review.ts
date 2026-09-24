import { z } from "zod";

const count = z.int().nonnegative();

const moneyAmountString = z
  .string()
  .regex(/^\d+(?:\.\d+)?$/)
  .refine((val) => Number.parseFloat(val) > 0, {
    message: "Money amount must be greater than 0",
  });

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

export const reviewCostSchema = z.object({
  status: z.enum([
    "estimated",
    "unsupported-model",
    "usage-unavailable",
    "not-applicable",
  ]),
  estimatedUsd: moneyAmountString,
  pricingVersion: z.iso.date(),
  partial: z.boolean(),
});

export const modelUsageSchema = z.object({
  model: z.string(),
  requestCount: count,
  inputTokens: count,
  cachedInputTokens: count,
  outputTokens: count,
  reasoningTokens: count,
});

export const reviewUsageSchema = z.object({
  provider: z.string(),
  requestCount: count,
  inputTokens: count,
  cachedInputTokens: count,
  outputTokens: count,
  reasoningTokens: count,
  totalTokens: count,
  models: z.array(modelUsageSchema),
});

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
      usage: reviewUsageSchema,
      cost: reviewCostSchema,
    })
    .strict(),

  z
    .object({
      reviewId: z.uuid(),
      status: z.literal("failed"),
      error: z.string().min(1).max(2000),
      usage: reviewUsageSchema,
      cost: reviewCostSchema,
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

const apiDateSchema = z.iso.datetime().transform((value) => new Date(value));

export const repositoryReviewSchema = z
  .object({
    id: z.uuid(),
    repositoryId: z.uuid(),
    pullRequestNumber: z.number().int(),
    status: reviewStatusSchema,
    result: reviewResultSchema.nullable(),
    error: z.string().nullable(),
    startedAt: apiDateSchema.nullable(),
    finishedAt: apiDateSchema.nullable(),
    updatedAt: apiDateSchema,
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
