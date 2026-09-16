import { and, desc, eq, sql } from "drizzle-orm"

import { db } from "@/db/drizzle"
import { repository, review } from "@/db/schema"


export type ConnectedRepository = {
  id: string,
  name: string,
  reviewedPullRequests: number,
  reviewInProgress: boolean,
}

export type DashboardOverview = {
  metrics: {
    reviewsThisWeek: number
    issuesCaught: number
    averageReviewTimeMinutes: number | null
  }
  connectedRepositories: ConnectedRepository[]
}

export type Review = {
  id: string
  pullRequestTitle: string
  repository: string
  reviewedAt: string
  issuesFound: number
}

export async function getDashboardOverview(
  userId: string
): Promise<DashboardOverview> {
  const connectedRepositories = await db
    .select({
      id: repository.id,
      name: repository.fullName,
      reviewedPullRequests: sql<number>`count(distinct ${review.pullRequestNumber}) filter (where ${review.status} = 'finished')::int`,
      reviewInProgress: sql<boolean>`coalesce(bool_or(${review.status} in ('scheduled', 'running')), false)`,
    })
    .from(repository)
    .leftJoin(review, eq(review.repositoryId, repository.id))
    .where(eq(repository.userId, userId))
    .groupBy(repository.id)
    .orderBy(desc(repository.createdAt))

  return {
    metrics: {
      reviewsThisWeek: 0,
      issuesCaught: 0,
      averageReviewTimeMinutes: null
    },
    connectedRepositories: connectedRepositories,
  }
}

export async function getRepositoryReviews(
  userId: string,
  repositoryName: string,
) {
  return db
    .select({
      id: review.id,
      repositoryId: review.repositoryId,
      pullRequestNumber: review.pullRequestNumber,
      result: review.result,
      status: review.status,
      error: review.error,
      startedAt: review.startedAt,
      finishedAt: review.finishedAt,
      updatedAt: review.updatedAt,
      createdAt: review.createdAt,
    })
    .from(review)
    .innerJoin(repository, eq(review.repositoryId, repository.id))
    .where(
      and(
        eq(repository.userId, userId),
        eq(repository.fullName, repositoryName),
      ),
    )
    .orderBy(desc(review.createdAt))
    .limit(100);
}

export async function getRecentReviews(userId: string): Promise<Review[]> {
  void userId

  return []
}
