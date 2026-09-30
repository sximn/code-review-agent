import { applyReviewState } from "@/lib/review-state";
import { internalImplementer } from "../contract-implementer";
import { requireWorker } from "../middleware/internal-worker";
import { internalWorkerContract } from "../../contract/internal-worker";

const updateReviewState = internalImplementer
  .use(requireWorker)
  .internal.worker.updateReviewState.handler(async ({ input, errors }) => {
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

type InternalWorkerHandlers = {
  [K in keyof typeof internalWorkerContract]: ReturnType<
    (typeof internalImplementer)["internal"]["worker"][K]["handler"]
  >;
};

export const internalWorkerHandlers = {
  updateReviewState: updateReviewState,
} satisfies InternalWorkerHandlers;
