import { z } from "zod";
import { oc } from "@orpc/contract";
import {
  reviewStateSchema,
  reviewStatusSchema,
  reviewUsageInternalSchema,
} from "./schemas/review";
import { openapi } from "@orpc/openapi";

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

export const internalWorkerContract = {
  updateReviewState: updateReviewState,
};
