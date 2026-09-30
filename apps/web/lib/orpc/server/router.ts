import { randomUUID } from "node:crypto";

import { implement } from "@orpc/server";
import { and, eq } from "drizzle-orm";

import { db } from "@/db/drizzle";
import { repository, review } from "@/db/schema";
import { auth } from "@/lib/auth";
import { getRepositoryReviewsById } from "@/lib/dashboard";
import { appContract, internalContract } from "@/lib/orpc/contracts";
import { enqueueReviewJob } from "@/lib/queue";
import { applyReviewState } from "@/lib/review-state";
import { getOpenPullRequests, getPublicRepository } from "@/lib/repositories";
import { hasValidWorkerToken } from "@/lib/worker-auth";

type RequestContext = {
  headers: Headers;
};

async function findConnectedRepository(userId: string, repositoryId: string) {
  const [connectedRepository] = await db
    .select()
    .from(repository)
    .where(and(eq(repository.userId, userId), eq(repository.id, repositoryId)))
    .limit(1);

  return connectedRepository ?? null;
}

const app = implement(appContract).$context<RequestContext>();
const requireSession = app.middleware(async ({ context, next, errors }) => {
  const session = await auth.api.getSession({ headers: context.headers });
  if (!session) {
    throw errors.UNAUTHORIZED();
  }

  return next({ context: { session } });
});
const authed = app.use(requireSession);

const checkRepository = authed.repositories.check.handler(
  async ({ input, errors }) => {
    try {
      const publicRepository = await getPublicRepository(input.repository);
      if (!publicRepository) {
        throw errors.REPOSITORY_NOT_FOUND({
          message:
            "We couldn't find a public repository with that name. Private repositories aren't supported yet.",
        });
      }

      return { repository: publicRepository };
    } catch (error) {
      if (
        error instanceof Error &&
        "code" in error &&
        error.code === "REPOSITORY_NOT_FOUND"
      ) {
        throw error;
      }
      throw errors.GITHUB_UNAVAILABLE();
    }
  },
);

const connectRepository = authed.repositories.connect.handler(
  async ({ input, context, errors }) => {
    let publicRepository;
    try {
      publicRepository = await getPublicRepository(input.repository);
    } catch {
      throw errors.GITHUB_UNAVAILABLE();
    }

    if (!publicRepository) {
      throw errors.REPOSITORY_NOT_FOUND({
        message:
          "We couldn't verify that public repository. Private repositories aren't supported yet.",
      });
    }

    try {
      const [existingRepository] = await db
        .select()
        .from(repository)
        .where(
          and(
            eq(repository.userId, context.session.user.id),
            eq(repository.fullName, publicRepository.fullName),
          ),
        )
        .limit(1);

      if (existingRepository) {
        return {
          repository: {
            id: existingRepository.id,
            fullName: existingRepository.fullName,
          },
        };
      }

      const [createdRepository] = await db
        .insert(repository)
        .values({
          id: crypto.randomUUID(),
          fullName: publicRepository.fullName,
          userId: context.session.user.id,
        })
        .returning();

      return {
        repository: {
          id: createdRepository.id,
          fullName: createdRepository.fullName,
        },
      };
    } catch {
      throw errors.REPOSITORY_SAVE_FAILED();
    }
  },
);

const listPullRequests = authed.repositories.pullRequests.handler(
  async ({ input, context, errors }) => {
    const connectedRepository = await findConnectedRepository(
      context.session.user.id,
      input.repositoryId,
    );
    if (!connectedRepository) {
      throw errors.REPOSITORY_NOT_FOUND();
    }

    try {
      const result = await getOpenPullRequests(connectedRepository.fullName, {
        page: input.page,
        perPage: input.perPage,
      });
      if (!result) {
        throw errors.REPOSITORY_NOT_FOUND({
          message:
            "We couldn't fetch open pull requests. Private repositories aren't supported yet.",
        });
      }

      return {
        pullRequests: result.pullRequests,
        nextPage: result.hasNextPage ? input.page + 1 : null,
      };
    } catch (error) {
      if (
        error instanceof Error &&
        "code" in error &&
        error.code === "REPOSITORY_NOT_FOUND"
      ) {
        throw error;
      }
      throw errors.GITHUB_UNAVAILABLE({
        message:
          "We couldn't fetch open pull requests from this repository. Please try again.",
      });
    }
  },
);

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
    let createdReview: typeof review.$inferSelect;
    try {
      [createdReview] = await db
        .insert(review)
        .values({
          id: reviewId,
          repositoryId: connectedRepository.id,
          pullRequestNumber: input.pullRequestNumber,
          status: "scheduled",
        })
        .returning();
    } catch (error) {
      console.error("Could not create review", error);
      throw errors.REVIEW_CREATE_FAILED();
    }

    try {
      await enqueueReviewJob(reviewId, {
        repository: connectedRepository.fullName,
        pull_request: input.pullRequestNumber,
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

export const appRouter = app.router({
  repositories: {
    check: checkRepository,
    connect: connectRepository,
    pullRequests: listPullRequests,
  },
  reviews: {
    list: listReviews,
    create: createReview,
  },
});

const internal = implement(internalContract).$context<RequestContext>();
const requireWorker = internal.middleware(async ({ context, next, errors }) => {
  if (!hasValidWorkerToken(context.headers)) {
    throw errors.UNAUTHORIZED();
  }
  return next();
});

const updateReviewState = internal
  .use(requireWorker)
  .internal.reviews.updateState.handler(async ({ input, errors }) => {
    const result = await applyReviewState(input);

    if (result.kind === "updated") {
      return { review: result.review, usage: result.usage };
    }
    if (result.kind === "idempotent") {
      return { review: result.review };
    }
    if (result.kind === "not-found") {
      throw errors.REVIEW_NOT_FOUND();
    }

    throw errors.REVIEW_STATE_CONFLICT({
      message: `Cannot change review from ${result.currentStatus} to ${input.status}.`,
      data: { currentStatus: result.currentStatus },
    });
  });

export const internalRouter = internal.router({
  internal: {
    reviews: {
      updateState: updateReviewState,
    },
  },
});

export const apiRouter = {
  ...appRouter,
  ...internalRouter,
};
