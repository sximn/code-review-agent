"use client"

import * as React from "react"
import { MotionConfig, useReducedMotion } from "motion/react"

import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { MetricGrid } from "@/components/dashboard/metric-grid"
import { RepositoryWorkspace } from "@/components/dashboard/repository-workspace"
import type { DashboardOverview as DashboardOverviewType } from "@/lib/dashboard"

type DashboardOverviewProps = {
  overview: DashboardOverviewType
  userName: string
}

export function DashboardOverview({ overview, userName }: DashboardOverviewProps) {
  const { metrics } = overview
  const isEmpty = !overview.connectedRepositories || overview.connectedRepositories.length === 0;
  const reduceMotion = useReducedMotion()
  const [configuringRepository, setConfiguringRepository] = React.useState(false)
  const [repository, setRepository] = React.useState("")

  function openRepositorySetup() {
    setConfiguringRepository(true)

    requestAnimationFrame(() => {
      document.getElementById("repository-setup")?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "start",
      })
    })
  }

  function closeRepositorySetup() {
    requestAnimationFrame(() => {
      document.getElementById("review-metrics")?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "center",
      })
    })

    setConfiguringRepository(false)
    setRepository("")
  }

  function completeRepositorySetup() {
    setConfiguringRepository(false)
    setRepository("")
  }

  return (
    <MotionConfig
      reducedMotion="user"
      transition={{
        layout: reduceMotion
          ? { duration: 0 }
          : { type: "spring", stiffness: 320, damping: 34, mass: 0.9 },
      }}
    >
      <main
        className="flex flex-1 flex-col bg-[radial-gradient(circle_at_28%_18%,rgba(234,247,255,0.7),transparent_28rem),radial-gradient(circle_at_88%_85%,rgba(232,227,255,0.45),transparent_22rem)] dark:bg-[radial-gradient(circle_at_28%_18%,rgba(11,18,32,0.6),transparent_28rem),radial-gradient(circle_at_88%_85%,rgba(18,17,42,0.45),transparent_22rem)]"
      >
        <div className="mx-auto w-full max-w-6xl px-5 py-2 sm:px-8 sm:py-4">
          <DashboardHeader
            isEmpty={isEmpty}
            userName={userName}
            onConfigure={openRepositorySetup}
          />
          <MetricGrid metrics={metrics} isEmpty={isEmpty} />
          <RepositoryWorkspace
            isEmpty={isEmpty}
            configuring={configuringRepository}
            repository={repository}
            connectedRepositories={overview.connectedRepositories}
            setRepository={setRepository}
            onConfigure={openRepositorySetup}
            onClose={closeRepositorySetup}
            onComplete={completeRepositorySetup}
          />
        </div>
      </main>
    </MotionConfig>
  )
}
