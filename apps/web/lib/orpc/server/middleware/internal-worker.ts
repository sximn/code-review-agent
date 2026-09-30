import { hasValidWorkerToken } from "@/lib/worker-auth";
import { internalImplementer } from "../contract-implementer";

export const requireWorker = internalImplementer.middleware(
  async ({ context, next, errors }) => {
    if (!hasValidWorkerToken(context.headers)) {
      throw errors.UNAUTHORIZED();
    }
    return next();
  },
);
