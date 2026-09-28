import { timingSafeEqual } from "node:crypto";

import { and, eq, inArray, sql } from "drizzle-orm";

import { db } from "@/db/drizzle";
import { CreateReviewUsage, review, reviewUsage } from "@/db/schema";
import env from "@/lib/environment";
import { reviewStateSchema } from "@/lib/contracts/review";

function hasValidWorkerToken(request: Request): boolean {
  const received = request.headers.get("authorization") ?? "";
  const expected = `Bearer ${env.WORKER_API_TOKEN}`;
  const receivedBuffer = Buffer.from(received);
  const expectedBuffer = Buffer.from(expected);

  return (
    receivedBuffer.length === expectedBuffer.length &&
    timingSafeEqual(receivedBuffer, expectedBuffer)
  );
}

export async function PATCH(request: Request) {
  if (!hasValidWorkerToken(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const parsed = reviewStateSchema.safeParse(
    await request.json().catch(() => null),
  );
  if (!parsed.success) {
    return Response.json(
      {
        error: "Invalid review state payload.",
        issues: parsed.error.issues,
      },
      { status: 400 },
    );
  }

  const input = parsed.data;
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
            usage: input.usage,
            cost: input.cost,
            error: null,
            finishedAt: new Date(),
            updatedAt: new Date(),
          }
        : {
            status: input.status,
            result: null,
            error: input.error,
            usage: input.usage,
            cost: input.cost,
            finishedAt: new Date(),
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

    let recordedUsage: CreateReviewUsage | null = null;
    if (values.status === "failed" || values.status === "finished") {
      const [insertedUsage] = await tx
        .insert(reviewUsage)
        .values({
          id: crypto.randomUUID(),
          reviewId: input.reviewId,
          requestCount: values.usage.requestCount,
          responsesWithUsage: values.usage.requestCount,
          inputTokens: values.usage.requestCount,
          cachedInputTokens: values.usage.requestCount,
          cacheWriteTokens: values.usage.requestCount,
          outputTokens: values.usage.requestCount,
          reasoningTokens: values.usage.requestCount,
          totalTokens: values.usage.requestCount,
          estimatedCostUsd: values.cost.estimatedUsd,
        })
        .returning();
      recordedUsage = insertedUsage;
    }

    return { updatedReview, recordedUsage };
  });

  if (updatedReview) {
    return Response.json({ review: updatedReview, usage: recordedUsage });
  }

  // if no row was updated, we check what happened
  const [currentReview] = await db
    .select({ id: review.id, status: review.status })
    .from(review)
    .where(eq(review.id, input.reviewId))
    .limit(1);

  if (!currentReview) {
    return Response.json({ error: "Review not found." }, { status: 404 });
  }

  // callback was called again, or a message was reclaimed after worker already finished
  // that is valid and can happen, but we cannot override the stored data here
  if (
    currentReview.status === input.status ||
    (input.status === "running" &&
      (currentReview.status === "failed" ||
        currentReview.status === "finished"))
  ) {
    return Response.json({ review: currentReview });
  }

  return Response.json(
    {
      error: `Cannot change review from ${currentReview.status} to ${input.status}.`,
    },
    { status: 409 },
  );
}
