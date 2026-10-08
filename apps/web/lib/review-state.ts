import { and, eq, inArray, sql } from "drizzle-orm";

import { db } from "@/db/drizzle";
import { review, reviewUsage } from "@/db/schema";
import type { ReviewState } from "@/lib/orpc/contract/schemas/review";

export type ApplyReviewStateResult =
  | {
      kind: "updated";
      review: {
        id: string;
        status: (typeof review.$inferSelect)["status"];
      };
      usage: typeof reviewUsage.$inferSelect | null;
    }
  | {
      kind: "idempotent";
      review: {
        id: string;
        status: (typeof review.$inferSelect)["status"];
      };
    }
  | { kind: "not-found" }
  | {
      kind: "conflict";
      currentStatus: (typeof review.$inferSelect)["status"];
    };

export async function applyReviewState(
  input: ReviewState,
): Promise<ApplyReviewStateResult> {
  const previousStatuses =
    input.status === "running"
      ? (["scheduled"] as const)
      : input.status === "finished"
        ? (["running"] as const)
        : (["scheduled", "running"] as const);

  const values =
    input.status === "running"
      ? {
          status: input.status,
          startedAt: sql<Date>`coalesce(${review.startedAt}, now())`,
          finishedAt: null,
          error: null,
          updatedAt: new Date(),
        }
      : input.status === "finished"
        ? {
            status: input.status,
            result: input.result,
            error: null,
            finishedAt: input.completed_at
              ? new Date(input.completed_at)
              : new Date(),
            updatedAt: new Date(),
          }
        : {
            status: input.status,
            result: null,
            error: input.error,
            finishedAt: input.completed_at
              ? new Date(input.completed_at)
              : new Date(),
            updatedAt: new Date(),
          };

  const { updatedReview, recordedUsage } = await db.transaction(async (tx) => {
    const [updatedReview] = await tx
      .update(review)
      .set(values)
      .where(
        and(
          eq(review.id, input.reviewId),
          inArray(review.status, previousStatuses),
        ),
      )
      .returning({ id: review.id, status: review.status });

    let recordedUsage: typeof reviewUsage.$inferSelect | null = null;
    if (updatedReview && input.status !== "running" && input.usage) {
      const [insertedUsage] = await tx
        .insert(reviewUsage)
        .values({
          id: crypto.randomUUID(),
          reviewId: input.reviewId,
          requestCount: input.usage.request_count,
          responsesWithUsage: input.usage.responses_with_usage,
          inputTokens: input.usage.input_tokens,
          cachedInputTokens: input.usage.cached_input_tokens,
          cacheWriteTokens: input.usage.cache_write_tokens,
          outputTokens: input.usage.output_tokens,
          reasoningTokens: input.usage.reasoning_tokens,
          totalTokens: input.usage.total_tokens,
          estimatedCostUsd: input.cost?.estimated_usd ?? null,
        })
        .returning();
      recordedUsage = insertedUsage;
    }

    return { updatedReview, recordedUsage };
  });

  if (updatedReview) {
    return { kind: "updated", review: updatedReview, usage: recordedUsage };
  }

  const [currentReview] = await db
    .select({ id: review.id, status: review.status })
    .from(review)
    .where(eq(review.id, input.reviewId))
    .limit(1);

  if (!currentReview) {
    return { kind: "not-found" };
  }

  if (
    currentReview.status === input.status ||
    (input.status === "running" &&
      (currentReview.status === "failed" ||
        currentReview.status === "finished"))
  ) {
    return { kind: "idempotent", review: currentReview };
  }

  return { kind: "conflict", currentStatus: currentReview.status };
}
