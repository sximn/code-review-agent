import { randomUUID } from "node:crypto";

import { db } from "@/db/drizzle";
import { repository as repositoryTable, review } from "@/db/schema";
import { auth } from "@/lib/auth";
import { getRepositoryReviews } from "@/lib/dashboard";
import { enqueueReviewJob } from "@/lib/queue";
import { checkRepositoryRequest } from "@/lib/repositories";
import { and, eq } from "drizzle-orm";
import { getAsPositiveInteger } from "@/lib/nums";
import z from "zod";
import {
  createReviewResponseSchema,
  reviewsResponseSchema,
} from "@/lib/contracts/review";

export async function GET(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers });

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const repoCheck = await checkRepositoryRequest(request);
  if (!repoCheck.success) {
    return Response.json({ error: repoCheck.error }, { status: 400 });
  }

  const reviews = await getRepositoryReviews(
    session.user.id,
    repoCheck.repository,
  );

  const response: z.infer<typeof reviewsResponseSchema> = {
    reviews,
  };

  return Response.json(response);
}

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers });

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const repoCheck = await checkRepositoryRequest(request);
  if (!repoCheck.success) {
    return Response.json(
      { error: "Enter a repository in owner/repository format." },
      { status: 400 },
    );
  }

  const prInput = new URL(request.url).searchParams.get("pullRequestNumber");
  const pullRequestNumber = getAsPositiveInteger(prInput);
  if (!pullRequestNumber) {
    return Response.json(
      { error: "Missing pull request ID." },
      { status: 400 },
    );
  }

  try {
    const [connectedRepository] = await db
      .select()
      .from(repositoryTable)
      .where(
        and(
          eq(repositoryTable.userId, session.user.id),
          eq(repositoryTable.fullName, repoCheck.repository),
        ),
      )
      .limit(1);

    if (!connectedRepository) {
      return Response.json(
        { error: "Given repository not connected." },
        { status: 400 },
      );
    }

    const reviewId = randomUUID();
    const [createdReview] = await db
      .insert(review)
      .values({
        id: reviewId,
        repositoryId: connectedRepository.id,
        pullRequestNumber,
        status: "scheduled",
      })
      .returning();

    try {
      await enqueueReviewJob(reviewId, {
        repository: repoCheck.repository,
        pull_request: pullRequestNumber,
      });
    } catch (error) {
      console.error("Could not enqueue review", error);
      await db
        .update(review)
        .set({
          status: "failed",
          error: "The review could not be queued.",
          finishedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(review.id, reviewId));

      return Response.json(
        { error: "The review could not be queued. Please try again." },
        { status: 502 },
      );
    }

    const response: z.infer<typeof createReviewResponseSchema> = {
      review: createdReview,
    };
    return Response.json(response, { status: 201 });
  } catch (error) {
    console.error("Could not create review", error);
    return Response.json(
      { error: "We couldn't create this review. Please try again." },
      { status: 502 },
    );
  }
}
