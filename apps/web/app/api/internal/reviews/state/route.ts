import { timingSafeEqual } from "node:crypto"

import { and, eq, inArray, sql } from "drizzle-orm"
import { z } from "zod"

import { db } from "@/db/drizzle"
import { review } from "@/db/schema"
import env from "@/lib/environment"

const reviewStateSchema = z.discriminatedUnion("status", [
  z.object({
    reviewId: z.uuid(),
    status: z.literal("running"),
  }).strict(),
  z.object({
    reviewId: z.uuid(),
    status: z.literal("finished"),
    result: z.record(z.string(), z.unknown()),
  }).strict(),
  z.object({
    reviewId: z.uuid(),
    status: z.literal("failed"),
    error: z.string().min(1).max(2000),
  }).strict(),
])

function hasValidWorkerToken(request: Request): boolean {
  const received = request.headers.get("authorization") ?? ""
  const expected = `Bearer ${env.WORKER_API_TOKEN}`
  const receivedBuffer = Buffer.from(received)
  const expectedBuffer = Buffer.from(expected)

  return (
    receivedBuffer.length === expectedBuffer.length &&
    timingSafeEqual(receivedBuffer, expectedBuffer)
  )
}

export async function PATCH(request: Request) {
  if (!hasValidWorkerToken(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 })
  }

  const parsed = reviewStateSchema.safeParse(
    await request.json().catch(() => null),
  )
  if (!parsed.success) {
    return Response.json(
      { error: "Invalid review state payload." },
      { status: 400 },
    )
  }

  const input = parsed.data
  const previousStatuses =
    input.status === "running"
      ? (["scheduled"] as const)
      : input.status === "finished"
        ? (["running"] as const)
        : (["scheduled", "running"] as const)

  const values = input.status === "running"
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
          finishedAt: new Date(),
          updatedAt: new Date(),
        }
      : {
          status: input.status,
          result: null,
          error: input.error,
          finishedAt: new Date(),
          updatedAt: new Date(),
        }

  const [updatedReview] = await db
    .update(review)
    .set(values)
    .where(
      and(
        eq(review.id, input.reviewId),
        inArray(review.status, previousStatuses),
      ),
    )
    .returning({ id: review.id, status: review.status })

  if (updatedReview) {
    return Response.json({ review: updatedReview })
  }

  const [currentReview] = await db
    .select({ id: review.id, status: review.status })
    .from(review)
    .where(eq(review.id, input.reviewId))
    .limit(1)

  if (!currentReview) {
    return Response.json({ error: "Review not found." }, { status: 404 })
  }

  // A repeated callback, or a reclaimed message whose previous worker already
  // reached a terminal state, is successful and must not overwrite stored data.
  if (
    currentReview.status === input.status ||
    (input.status === "running" &&
      (currentReview.status === "failed" || currentReview.status === "finished"))
  ) {
    return Response.json({ review: currentReview })
  }

  return Response.json(
    {
      error: `Cannot change review from ${currentReview.status} to ${input.status}.`,
    },
    { status: 409 },
  )
}
