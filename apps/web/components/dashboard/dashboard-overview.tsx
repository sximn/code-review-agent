import Link from "next/link"
import { ArrowRight, Code2, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import type { DashboardOverview } from "@/lib/dashboard"

type DashboardOverviewProps = {
  overview: DashboardOverview
  userName: string
}

type MetricProps = {
  label: string
  value: string
  description: string
  bordered?: boolean
}

function greet(): (name: string) => string {
  const GREETINGS = [
    (name: string) => `Good to see you, ${name}.`,
    (name: string) => `Welcome back, ${name}.`,
    (name: string) => `Ready when you are, ${name}.`,
    (name: string) => `Let's make progress, ${name}.`,
    (name: string) => `Here's what's happening, ${name}.`,
    (name: string) => `Your workspace is ready, ${name}.`,
    (name: string) => `Time to build, ${name}.`,
    (name: string) => `Let's get after it, ${name}.`,
    (name: string) => `Another great day to ship, ${name}.`,
    (name: string) => `What are we tackling today, ${name}?.`,
    (name: string) => `Back in action, ${name}.`,
    (name: string) => `Let's make something happen, ${name}.`,
    (name: string) => `Your next move starts here, ${name}.`,
    (name: string) => `All systems ready, ${name}.`,
    (name: string) => `Let's keep things moving, ${name}.`,
    (name: string) => `You've got this, ${name}.`,
    (name: string) => `Ready to make an impact, ${name}?.`,
    (name: string) => `One step closer, ${name}.`,
    (name: string) => `Let's turn ideas into action, ${name}.`,
    (name: string) => `Welcome to your command center, ${name}.`,
  ];

  const today = new Date().toISOString().slice(0, 10);
  let seed = 0;
  for (const char of today) {
    seed = (seed * 31 + char.charCodeAt(0)) >>> 0;
  }

  return GREETINGS[seed % GREETINGS.length];
}

function Metric({ label, value, description, bordered = false }: MetricProps) {
  return (
    <Card
      className={`gap-0 rounded-none border-0 bg-transparent p-0 py-2 shadow-none ring-0 sm:px-7 ${
        bordered ? "sm:border-r sm:border-border/50" : ""
      }`}
    >
      <p className="text-sm text-muted-foreground">{label}</p>
      <strong className="mt-3 text-4xl font-normal tracking-[-0.08em] text-foreground">
        {value}
      </strong>
      <span className="mt-2 text-sm text-muted-foreground">{description}</span>
    </Card>
  )
}

export function DashboardOverview({
  overview,
  userName
}: DashboardOverviewProps) {
  const { metrics } = overview
  const isEmpty = !overview.hasConnectedRepository

  const greetWithName = isEmpty ? (n: string) => `Whenever you are ready, ${n}.` : greet();

  return (
    <main className="flex flex-col flex-1 bg-[radial-gradient(circle_at_28%_18%,rgba(234,247,255,0.7),transparent_28rem),radial-gradient(circle_at_88%_85%,rgba(232,227,255,0.45),transparent_22rem)] dark:bg-[radial-gradient(circle_at_28%_18%,rgba(11,18,32,0.6),transparent_28rem),radial-gradient(circle_at_88%_85%,rgba(18,17,42,0.45),transparent_22rem)]">
      <div className="mx-auto w-full max-w-6xl px-5 py-2 sm:px-8 sm:py-4">
        <section
          className="flex flex-col gap-8 pb-5 sm:pb-6 lg:flex-row lg:items-end lg:justify-between"
          aria-labelledby="dashboard-heading"
        >
          <div>
            <h1
              id="dashboard-heading"
              className="text-2xl font-semibold tracking-[-0.055em] text-foreground sm:text-3xl"
            >
              Dashboard
            </h1>
            <p className="mt-1 text-lg text-foreground/80 sm:text-xl">
              {greetWithName(userName)}
            </p>
            <p className="mt-1 text-sm text-muted-foreground sm:text-md">
              {isEmpty
                ? "Your codebase is quiet. That's a good place to start."
                : "Here is what your team has caught this week."}
            </p>
          </div>

          <Button
            render={<Link href="#repository-setup" />}
            nativeButton={false}
            className="group gap-2 max-w-sm"
          >
            <Plus aria-hidden="true" size={18} className=" group-hover:rotate-90 transition-transform duration-300" />
            Configure repository
            <ArrowRight aria-hidden="true" size={18} />
          </Button>
        </section>

        <section
          className="grid border-y border-border/50 sm:grid-cols-3"
          aria-label="Review metrics"
        >
          <Metric
            label="Reviews this week"
            value={metrics.reviewsThisWeek ? String(metrics.reviewsThisWeek) : "—"}
            description={isEmpty ? "Awaiting your first repo" : "Completed reviews"}
            bordered
          />
          <Metric
            label="Issues caught"
            value={metrics.issuesCaught ? String(metrics.issuesCaught) : "—"}
            description={isEmpty ? "Insights will appear here" : "Across reviewed pull requests"}
            bordered
          />
          <Metric
            label="Avg. review time"
            value={
              metrics.averageReviewTimeMinutes
                ? `${metrics.averageReviewTimeMinutes}m`
                : "—"
            }
            description={isEmpty ? "Powered by REWY" : "From pull request to result"}
          />
        </section>

        <div className="relative min-h-105 isolate mt-4 mx-auto grid max-w-260 place-items-center overflow-hidden rounded-[15px] border bg-[linear-gradient(135deg,#f4f8ff,#fff_52%,#f3f7ff)] shadow-[0_16px_40px_rgba(48,76,125,0.04)] border-border dark:bg-[linear-gradient(135deg,#0b1220,#111827_52%,#0a1020)] dark:shadow-[0_16px_40px_rgba(0,0,0,0.25)]">
          <div className="pointer-events-none absolute inset-0 opacity-[0.55] bg-[linear-gradient(#dce6f5_1px,transparent_1px),linear-gradient(90deg,#dce6f5_1px,transparent_1px)] bg-size-[45px_45px] mask-[linear-gradient(transparent,black_30%,black_65%,transparent)] dark:opacity-25 dark:bg-[linear-gradient(#263753_1px,transparent_1px),linear-gradient(90deg,#263753_1px,transparent_1px)]" />

          <div className="pointer-events-none absolute -bottom-45 -left-31.25 size-87.5 rounded-full border border-[#bdd2f8] opacity-50 dark:border-[#29466f] dark:opacity-60" />
          <div className="pointer-events-none absolute -right-35 -top-42.5 size-87.5 rounded-full border border-[#bdd2f8] opacity-50 animate-[drift_8s_ease-in-out_infinite_-3s] dark:border-[#29466f] dark:opacity-60" />

          <div className="relative max-w-md p-7.5 text-center flex flex-col items-center">
            <div className="grid size-10 place-items-center rounded-xl border border-border bg-background text-foreground">
              <Code2 aria-hidden="true" size={24} strokeWidth={2.25} />
            </div>

            <h2
              id="review-space-heading"
              className="mt-2 text-2xl font-medium tracking-[-0.055em] text-foreground sm:text-3xl"
            >
              {isEmpty ? "Nothing reviewed yet." : "Your latest reviews."}
            </h2>

            <p className="mt-2 max-w-sm text-sm leading-4 text-muted-foreground">
              {isEmpty
                ? "Connect a repository and REWY will start looking for what your team might miss."
                : "New reviews will appear here as your pull requests are analyzed."}
            </p>

            {isEmpty && (
              <Button
                render={<Link href="#repository-setup" />}
                nativeButton={false}
                variant="outline"
                size="lg"
                className="mt-7 gap-2"
              >
                Set up your first repository
                <ArrowRight aria-hidden="true" size={17} />
              </Button>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
