import { desc, eq } from "drizzle-orm"

import { db } from "@/db/drizzle"
import { repository } from "@/db/schema"


export type ConnectedRepository = {
  id: string,
  name: string,
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
    .select({ id: repository.id, name: repository.fullName })
    .from(repository)
    .where(eq(repository.userId, userId))
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

export async function getRecentReviews(userId: string): Promise<Review[]> {
  void userId

  return []
}
