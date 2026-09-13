export type DashboardOverview = {
  metrics: {
    reviewsThisWeek: number
    issuesCaught: number
    averageReviewTimeMinutes: number | null
  }
  hasConnectedRepository: boolean
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
  void userId

  return {
    metrics: {
      reviewsThisWeek: 0,
      issuesCaught: 0,
      averageReviewTimeMinutes: null
    },
    hasConnectedRepository: false
  }
}

export async function getRecentReviews(userId: string): Promise<Review[]> {
  void userId

  return []
}
