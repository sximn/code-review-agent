import { openapi } from "@orpc/openapi";
import { authenticated } from "./contract-builder";
import { repositoryErrors } from "./errors";
import {
  connectedRepositorySchema,
  publicRepositorySchema,
  pullRequestSchema,
  repositoryNameSchema,
} from "./schemas/repository";
import { z } from "zod";

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
    // REPOSITORY_SAVE_FAILED: repositoryErrors.REPOSITORY_SAVE_FAILED,
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

export const repositoryContract = {
  check: checkRepository,
  connect: connectRepository,
  pullRequests: listPullRequests,
};
