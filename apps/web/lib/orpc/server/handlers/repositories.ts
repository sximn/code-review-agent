import { getOpenPullRequests, getPublicRepository } from "@/lib/repositories";
import { appImplementer } from "../contract-implementer";
import { requireSession } from "../middleware/auth-session";
import { db } from "@/db/drizzle";
import { repository } from "@/db/schema";
import { and, eq } from "drizzle-orm";
import { findConnectedRepository } from "@/lib/dashboard";
import { repositoryContract } from "../../contract/repositories";

const authed = appImplementer.use(requireSession);

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

type RepositoryHandlers = {
  [K in keyof typeof repositoryContract]: ReturnType<
    (typeof authed)["repositories"][K]["handler"]
  >;
};

export const repositoryHandlers = {
  check: checkRepository,
  connect: connectRepository,
  pullRequests: listPullRequests,
} satisfies RepositoryHandlers;
