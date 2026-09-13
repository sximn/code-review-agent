import { ensureSessionServer } from "@better-auth-ui/core/server"
import { dehydrate, HydrationBoundary } from "@tanstack/react-query"
import { headers } from "next/headers"
import { redirect } from "next/navigation"

import { auth } from "@/lib/auth"
import { DashboardOverview } from "@/components/dashboard/dashboard-overview"
import { getDashboardOverview } from "@/lib/dashboard"
import { getQueryClient } from "@/lib/query-client"

export default async function Dashboard() {
  const queryClient = getQueryClient()

  const session = await ensureSessionServer(queryClient, auth, {
    headers: await headers()
  })

  if (!session) {
    redirect("/auth/sign-in?redirectTo=/dashboard")
  }

  const overview = await getDashboardOverview(session.user.id)
  const userName = session.user.name?.split(" ")[0] || "there"

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <DashboardOverview overview={overview} userName={userName} />
    </HydrationBoundary>
  )
}
