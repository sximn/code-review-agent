import { z } from "zod";

const count = z.int().nonnegative();

const moneyAmountString = z
  .string()
  .regex(/^\d+(?:\.\d+)?$/, "Money amount must be a non-negative decimal");

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
  .strict()
  .meta({ id: "Finding" });

export const reviewResultSchema = z
  .object({
    findings: z.array(findingSchema),
    approval_granted: z.boolean(),
  })
  .strict()
  .meta({ id: "ReviewResult" });

export const reviewCostSchema = z
  .object({
    status: z.enum([
      "estimated",
      "unsupported-model",
      "usage-unavailable",
      "not-applicable",
    ]),
    estimated_usd: moneyAmountString.nullable(),
    pricing_version: z.iso.date().nullable(),
    partial: z.boolean(),
    unsupported_models: z.array(z.string()),
  })
  .strict()
  .meta({ id: "ReviewCost" });

export const modelUsageSchema = z
  .object({
    model: z.string(),
    request_count: count,
    responses_with_usage: count,
    input_tokens: count,
    cached_input_tokens: count,
    cache_write_tokens: count,
    output_tokens: count,
    reasoning_tokens: count,
    total_tokens: count,
  })
  .strict()
  .meta({ id: "ModelUsage" });

export const reviewUsageSchema = z
  .object({
    provider: z.literal("openai"),
    request_count: count,
    responses_with_usage: count,
    responses_without_usage: count,
    input_tokens: count,
    cached_input_tokens: count,
    cache_write_tokens: count,
    output_tokens: count,
    reasoning_tokens: count,
    total_tokens: count,
    models: z.array(modelUsageSchema),
  })
  .strict()
  .meta({ id: "ReviewUsage" });

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
      usage: reviewUsageSchema.optional(),
      cost: reviewCostSchema.optional(),
    })
    .strict(),

  z
    .object({
      reviewId: z.uuid(),
      status: z.literal("failed"),
      error: z.string().min(1).max(2000),
      usage: reviewUsageSchema.optional(),
      cost: reviewCostSchema.optional(),
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

const apiDateSchema = z.date();

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
  .strict()
  .meta({ id: "RepositoryReview" });

export const reviewUsageInternalSchema = z
  .object({
    id: z.uuid(),
    reviewId: z.uuid(),
    requestCount: count,
    responsesWithUsage: count,
    inputTokens: count,
    cachedInputTokens: count,
    cacheWriteTokens: count,
    outputTokens: count,
    reasoningTokens: count,
    totalTokens: count,
    estimatedCostUsd: moneyAmountString.nullable(),
  })
  .strict()
  .meta({ id: "StoredReviewUsage" });

export const repositoryReviewWithUsageSchema = repositoryReviewSchema
  .extend({
    usage: reviewUsageInternalSchema.nullable(),
  })
  .meta({ id: "RepositoryReviewWithUsage" });

export const reviewsResponseSchema = z
  .object({
    reviews: z.array(repositoryReviewWithUsageSchema),
  })
  .strict();

export const createReviewResponseSchema = z
  .object({
    review: repositoryReviewSchema,
  })
  .strict();

export type ReviewUsageInternal = z.infer<typeof reviewUsageInternalSchema>;
export type RepositoryReview = z.infer<typeof repositoryReviewSchema>;
export type RepositoryReviewWithUsage = z.infer<
  typeof repositoryReviewWithUsageSchema
>;
export type ReviewsResponse = z.infer<typeof reviewsResponseSchema>;
