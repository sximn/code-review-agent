import { oc } from "@orpc/contract";
import { openapi } from "@orpc/openapi";
import { z } from "zod";

import {
  repositoryReviewSchema,
  repositoryReviewWithUsageSchema,
  reviewStatusSchema,
  reviewStateSchema,
  reviewUsageInternalSchema,
} from "@/lib/contracts/review";

const repositoryNameSchema = z
  .string()
  .trim()
  .regex(/^[^/\s]+\/[^/\s]+$/, "Use owner/repository format");

export const publicRepositorySchema = z
  .object({
    fullName: repositoryNameSchema,
  })
  .strict()
  .meta({ id: "PublicRepository" });

export const connectedRepositorySchema = z
  .object({
    id: z.uuid(),
    fullName: repositoryNameSchema,
  })
  .strict()
  .meta({ id: "ConnectedRepository" });

export const pullRequestSchema = z
  .object({
    number: z.int().positive(),
    url: z.url(),
    title: z.string(),
    description: z.string(),
    updatedAt: z.date(),
  })
  .strict()
  .meta({ id: "PullRequest" });

export type PullRequest = z.infer<typeof pullRequestSchema>;

const authenticated = oc.errors({
  UNAUTHORIZED: { message: "Unauthorized." },
});

const repositoryErrors = {
  INVALID_REPOSITORY: {
    message: "Enter a repository in owner/repository format.",
  },
  REPOSITORY_NOT_FOUND: {
    message: "The repository could not be found or is not connected.",
  },
  GITHUB_UNAVAILABLE: {
    message: "GitHub is unavailable. Please try again shortly.",
  },
};

const checkRepository = authenticated
  .errors(repositoryErrors)
  .meta(
    openapi({
      method: "POST",
      path: "/repositories/check",
      operationId: "checkRepository",
      summary: "Check access to a public GitHub repository",
      tags: ["Repositories"],
    }),
  )
  .input(z.object({ repository: repositoryNameSchema }).strict())
  .output(z.object({ repository: publicRepositorySchema }).strict());

const connectRepository = authenticated
  .errors({
    ...repositoryErrors,
    REPOSITORY_SAVE_FAILED: {
      message: "The repository could not be connected.",
    },
  })
  .meta(
    openapi({
      method: "POST",
      path: "/repositories",
      operationId: "connectRepository",
      summary: "Connect a public GitHub repository",
      tags: ["Repositories"],
    }),
  )
  .input(z.object({ repository: repositoryNameSchema }).strict())
  .output(z.object({ repository: connectedRepositorySchema }).strict());

const listPullRequests = authenticated
  .errors(repositoryErrors)
  .meta(
    openapi({
      method: "GET",
      path: "/repositories/{repositoryId}/pull-requests",
      operationId: "listRepositoryPullRequests",
      summary: "List open pull requests",
      tags: ["Repositories"],
    }),
  )
  .input(
    z
      .object({
        repositoryId: z.uuid(),
        page: z.coerce.number().int().positive().default(1),
        perPage: z.coerce.number().int().min(1).max(100).default(25),
      })
      .strict(),
  )
  .output(
    z
      .object({
        pullRequests: z.array(pullRequestSchema),
        nextPage: z.int().positive().nullable(),
      })
      .strict(),
  );

const listReviews = authenticated
  .errors({
    REPOSITORY_NOT_FOUND: repositoryErrors.REPOSITORY_NOT_FOUND,
  })
  .meta(
    openapi({
      method: "GET",
      path: "/repositories/{repositoryId}/reviews",
      operationId: "listRepositoryReviews",
      summary: "List recent reviews for a repository",
      tags: ["Reviews"],
    }),
  )
  .input(z.object({ repositoryId: z.uuid() }).strict())
  .output(
    z.object({ reviews: z.array(repositoryReviewWithUsageSchema) }).strict(),
  );

const createReview = authenticated
  .errors({
    REPOSITORY_NOT_FOUND: repositoryErrors.REPOSITORY_NOT_FOUND,
    REVIEW_QUEUE_UNAVAILABLE: {
      message: "The review could not be queued. Please try again.",
    },
    REVIEW_CREATE_FAILED: {
      message: "The review could not be created. Please try again.",
    },
  })
  .meta(
    openapi({
      method: "POST",
      path: "/repositories/{repositoryId}/reviews",
      operationId: "createRepositoryReview",
      summary: "Schedule a pull request review",
      successStatus: 201,
      tags: ["Reviews"],
    }),
  )
  .input(
    z
      .object({
        repositoryId: z.uuid(),
        pullRequestNumber: z.int().positive(),
      })
      .strict(),
  )
  .output(z.object({ review: repositoryReviewSchema }).strict());

export const appContract = {
  repositories: {
    check: checkRepository,
    connect: connectRepository,
    pullRequests: listPullRequests,
  },
  reviews: {
    list: listReviews,
    create: createReview,
  },
};

const updateReviewState = oc
  .errors({
    UNAUTHORIZED: { message: "Unauthorized." },
    REVIEW_NOT_FOUND: { message: "Review not found." },
    REVIEW_STATE_CONFLICT: {
      message: "The requested review state transition is not allowed.",
      data: z.object({ currentStatus: z.string() }).strict(),
    },
  })
  .meta(
    openapi({
      method: "PATCH",
      path: "/internal/reviews/{reviewId}/state",
      operationId: "updateReviewState",
      summary: "Persist a review worker state transition",
      tags: ["Internal Reviews"],
      spec: (operation) => ({
        ...operation,
        security: [{ workerBearer: [] }],
      }),
    }),
  )
  .input(reviewStateSchema)
  .output(
    z
      .object({
        review: z.object({ id: z.uuid(), status: reviewStatusSchema }).strict(),
        usage: reviewUsageInternalSchema.nullable().optional(),
      })
      .strict(),
  );

export const internalContract = {
  internal: {
    reviews: {
      updateState: updateReviewState,
    },
  },
};

export const apiContract = {
  ...appContract,
  ...internalContract,
};
