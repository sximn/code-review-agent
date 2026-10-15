import { defineRelations } from "drizzle-orm";
import * as schema from "./schema";

export const relations = defineRelations(schema, (r) => ({
  user: {
    sessions: r.many.session(),
    accounts: r.many.account(),
    repositories: r.many.repository(),
  },

  session: {
    user: r.one.user({
      from: r.session.userId,
      to: r.user.id,
    }),
  },

  account: {
    user: r.one.user({
      from: r.account.userId,
      to: r.user.id,
    }),
  },

  repository: {
    user: r.one.user({
      from: r.repository.userId,
      to: r.user.id,
    }),
    pullRequests: r.many.pullRequest(),
  },

  pullRequest: {
    repository: r.one.repository({
      from: r.pullRequest.repositoryId,
      to: r.repository.id,
    }),
    versions: r.many.pullRequestVersion(),
  },
  pullRequestVersion: {
    pullRequest: r.one.pullRequest({
      from: r.pullRequestVersion.pullRequestId,
      to: r.pullRequest.id,
    }),
    reviews: r.many.review(),
  },
  review: {
    pullRequestVersion: r.one.pullRequestVersion({
      from: r.review.pullRequestVersionId,
      to: r.pullRequestVersion.id,
    }),
  },
}));
