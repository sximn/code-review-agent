import { z } from "zod";
import { authenticated } from "./contract-builder";
import { repositoryErrors } from "./errors";
import { openapi } from "@orpc/openapi";
import {
  repositoryReviewSchema,
  repositoryReviewWithUsageSchema,
} from "./schemas/review";

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

export const reviewContract = {
  list: listReviews,
  create: createReview,
};
