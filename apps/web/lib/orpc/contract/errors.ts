import { COMMON_ERROR_STATUS_MAP } from "@orpc/openapi";
import { z } from "zod";

export const repositoryErrors = {
  INVALID_REPOSITORY: {
    message: "Enter a repository in owner/repository format.",
  },
  REPOSITORY_NOT_FOUND: {
    message: "The repository could not be found or is not connected.",
  },
  GITHUB_UNAVAILABLE: {
    message: "GitHub is unavailable. Please try again shortly.",
  },
  REPOSITORY_SAVE_FAILED: {
    message: "The repository could not be connected.",
  },
};
export const reviewErrors = {
  REVIEW_NOT_FOUND: { message: "Review not found." },
  REVIEW_STATE_CONFLICT: {
    message: "The requested review state transition is not allowed.",
    data: z.object({ currentStatus: z.string() }).strict(),
  },
  REVIEW_QUEUE_UNAVAILABLE: {
    message: "The review could not be queued. Please try again.",
  },
  REVIEW_CREATE_FAILED: {
    message: "The review could not be created. Please try again.",
  },
};

const repositoryErrorStatuses = {
  INVALID_REPOSITORY: 400,
  REPOSITORY_NOT_FOUND: 404,
  GITHUB_UNAVAILABLE: 502,
  REPOSITORY_SAVE_FAILED: 502,
} satisfies Record<keyof typeof repositoryErrors, number>;

const reviewErrorStatuses = {
  REVIEW_NOT_FOUND: 404,
  REVIEW_CREATE_FAILED: 502,
  REVIEW_STATE_CONFLICT: 409,
  REVIEW_QUEUE_UNAVAILABLE: 502,
} satisfies Record<keyof typeof reviewErrors, number>;

export const errorStatusMap = {
  ...COMMON_ERROR_STATUS_MAP,
  ...repositoryErrorStatuses,
  ...reviewErrorStatuses,
};
