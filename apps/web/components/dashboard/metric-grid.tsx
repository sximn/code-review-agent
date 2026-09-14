import { motion } from "motion/react"

import { Card } from "@/components/ui/card"
import type { DashboardOverview } from "@/lib/dashboard"

type MetricProps = {
  label: string
  value: string
  description: string
  bordered?: boolean
}

function Metric({
  label,
  value,
  description,
  bordered = false,
}: MetricProps) {
  return (
    <Card
      className={[
        "gap-0 rounded-none border-0 bg-transparent p-0 py-2 shadow-none ring-0 sm:px-7",
        bordered ? "sm:border-r sm:border-border/50" : "",
      ].join(" ")}
    >
      <dl>
        <dt className="text-sm text-muted-foreground">{label}</dt>
        <dd className="mt-3 text-4xl font-normal tracking-[-0.08em] text-foreground">
          {value}
        </dd>
        <dd className="mt-2 text-sm text-muted-foreground">
          {description}
        </dd>
      </dl>
    </Card>
  )
}

type MetricGridProps = {
  metrics: DashboardOverview["metrics"]
  isEmpty: boolean
}

export function MetricGrid({ metrics, isEmpty }: MetricGridProps) {
  return (
    <motion.section
      layout
      className="grid border-y border-border/50 sm:grid-cols-3"
      aria-label="Review metrics"
      id="review-metrics"
    >
      <Metric
        label="Reviews this week"
        value={
          metrics.reviewsThisWeek == null
            ? "—"
            : String(metrics.reviewsThisWeek)
        }
        description={isEmpty ? "Awaiting your first repo" : "Completed reviews"}
        bordered
      />
      <Metric
        label="Issues caught"
        value={metrics.issuesCaught == null ? "—" : String(metrics.issuesCaught)}
        description={
          isEmpty ? "Insights will appear here" : "Across reviewed pull requests"
        }
        bordered
      />
      <Metric
        label="Avg. review time"
        value={
          metrics.averageReviewTimeMinutes == null
            ? "—"
            : `${metrics.averageReviewTimeMinutes}m`
        }
        description={
          isEmpty ? "Powered by REWY" : "From pull request to result"
        }
      />
    </motion.section>
  )
}
