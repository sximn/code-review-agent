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
  metricsThisWeek: {
    reviews: number
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
  const [connectedRepositories, [metrics]] = await Promise.all([
    db
      .select({
        id: repository.id,
        name: repository.fullName,
        reviewedPullRequests: sql<number>`
          count(distinct ${review.pullRequestNumber})
          filter (where ${review.status} = 'finished')::int
        `,
        reviewInProgress: sql<boolean>`
          coalesce(
            bool_or(${review.status} in ('scheduled', 'running')),
            false
          )
        `,
      })
      .from(repository)
      .leftJoin(review, eq(review.repositoryId, repository.id))
      .where(eq(repository.userId, userId))
      .groupBy(repository.id)
      .orderBy(desc(repository.createdAt)),

    db
      .select({
        reviewsThisWeek: sql<number>`
          count(*)
          filter (
            where ${review.status} = 'finished'
              and ${review.finishedAt} >= date_trunc('week', current_timestamp)
          )::int
        `,
        issuesThisWeek: sql<number>`
          coalesce(
            sum(
              (
                select count(*)
                from jsonb_array_elements(
                  coalesce(${review.result} -> 'findings', '[]'::jsonb)
                ) as finding
                where finding ->> 'severity' in ('critical', 'high')
              )
            ) filter (
              where ${review.status} = 'finished'
                and ${review.result} is not null
                and ${review.finishedAt} >= date_trunc('week', current_timestamp)
            ),
            0
          )::int
        `,
        averageReviewTimeMinutesThisWeek: sql<number | null>`
          avg(
            extract(
              epoch from (${review.finishedAt} - ${review.startedAt})
            ) / 60.0
          )
          filter (
            where ${review.status} = 'finished'
              and ${review.startedAt} is not null
              and ${review.finishedAt} is not null
              and ${review.finishedAt} >= date_trunc('week', current_timestamp)
          )::float8
        `,
      })
      .from(review)
      .innerJoin(repository, eq(review.repositoryId, repository.id))
      .where(eq(repository.userId, userId)),
  ])

  const avgMinutesFourDecimal = metrics.averageReviewTimeMinutesThisWeek
    ? Math.round(metrics.averageReviewTimeMinutesThisWeek * 10000) / 10000
    : null;

  return {
    metricsThisWeek: {
      reviews: metrics.reviewsThisWeek,
      issuesCaught: metrics.issuesThisWeek,
      averageReviewTimeMinutes: avgMinutesFourDecimal,
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
