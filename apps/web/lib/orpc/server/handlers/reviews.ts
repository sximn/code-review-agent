import { db } from "@/db/drizzle";
import { appImplementer } from "../contract-implementer";
import { requireSession } from "../middleware/auth-session";
import {
  findConnectedRepository,
  getRepositoryReviewsById,
} from "@/lib/dashboard";
import { getPullRequest } from "@/lib/repositories";
import { recordPullRequestVersion } from "@/lib/pull-requests";
import { review } from "@/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { enqueueReviewJob } from "@/lib/queue";
import { reviewContract } from "../../contract/reviews";

const authed = appImplementer.use(requireSession);

const listReviews = authed.reviews.list.handler(
  async ({ input, context, errors }) => {
    const connectedRepository = await findConnectedRepository(
      context.session.user.id,
      input.repositoryId,
    );
    if (!connectedRepository) {
      throw errors.REPOSITORY_NOT_FOUND();
    }

    return {
      reviews: await getRepositoryReviewsById(
        context.session.user.id,
        input.repositoryId,
      ),
    };
  },
);

const createReview = authed.reviews.create.handler(
  async ({ input, context, errors }) => {
    const connectedRepository = await findConnectedRepository(
      context.session.user.id,
      input.repositoryId,
    );
    if (!connectedRepository) {
      throw errors.REPOSITORY_NOT_FOUND({
        message: "Given repository not connected.",
      });
    }

    const reviewId = randomUUID();
    let createdReview;

    try {
      const pr = await getPullRequest(
        connectedRepository.fullName,
        input.pullRequestNumber,
      );

      if (!pr) {
        throw new Error("Pull request not found");
      }

      createdReview = await db.transaction(async (tx) => {
        const version = await recordPullRequestVersion(
          tx,
          connectedRepository.id,
          pr.number,
          pr.headSha,
        );
        const [created] = await tx
          .insert(review)
          .values({
            id: reviewId,
            pullRequestVersionId: version.id,
            status: "scheduled",
          })
          .returning();

        return {
          ...created,
          repositoryId: connectedRepository.id,
          pullRequestNumber: pr.number,
          headSha: version.headSha,
        };
      });
    } catch (error) {
      console.error("Could not create review", error);
      throw errors.REVIEW_CREATE_FAILED();
    }

    try {
      await enqueueReviewJob(reviewId, {
        repository: connectedRepository.fullName,
        visibility: connectedRepository.isPrivate ? "private" : "public",
        pull_request: input.pullRequestNumber,
        head_sha: input.headSha,
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
      throw errors.REVIEW_QUEUE_UNAVAILABLE();
    }

    return { review: createdReview };
  },
);

type ReviewHandlers = {
  [K in keyof typeof reviewContract]: ReturnType<
    (typeof authed)["reviews"][K]["handler"]
  >;
};

export const reviewHandlers = {
  list: listReviews,
  create: createReview,
} satisfies ReviewHandlers;
