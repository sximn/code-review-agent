import { repositoryContract } from "./repositories";
import { reviewContract } from "./reviews";
import { internalWorkerContract } from "./internal-worker";

export const appContract = {
  repositories: repositoryContract,
  reviews: reviewContract,
};

export const internalContract = {
  internal: {
    worker: internalWorkerContract,
  },
};

export const apiContract = {
  ...appContract,
  ...internalContract,
};
