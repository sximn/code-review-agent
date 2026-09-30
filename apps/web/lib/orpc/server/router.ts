import { repositoryHandlers } from "./handlers/repositories";
import { reviewHandlers } from "./handlers/reviews";
import { internalWorkerHandlers } from "./handlers/internal-worker";
import { appImplementer, internalImplementer } from "./contract-implementer";

export const appRouter = appImplementer.router({
  repositories: repositoryHandlers,
  reviews: reviewHandlers,
});

export const internalRouter = internalImplementer.router({
  internal: {
    worker: internalWorkerHandlers,
  },
});

export const apiRouter = {
  ...appRouter,
  ...internalRouter,
};
