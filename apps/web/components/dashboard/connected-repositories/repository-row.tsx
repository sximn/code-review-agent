import { useState } from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { AnimatePresence, motion } from "motion/react"
import {
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  GitPullRequest,
  LoaderCircle,
  LoaderPinwheel,
  Send,
} from "lucide-react"
import { ConnectedRepository } from "@/lib/dashboard"
import { PullRequest } from "@/lib/repositories"
import { Button } from "@/components/ui/button"

const PULL_REQUESTS_PER_PAGE = 25;

type PullRequestsPage = {
  pullRequests: PullRequest[]
  nextPage: number | null
}

async function fetchPullRequests({
  repositoryName,
  page,
  signal,
}: {
  repositoryName: string
  page: number
  signal?: AbortSignal
}): Promise<PullRequestsPage> {
  const params = new URLSearchParams({
    repository: repositoryName,
    page: String(page),
    perPage: String(PULL_REQUESTS_PER_PAGE),
  })

  const response = await fetch(
    `/api/repositories/pull-requests?${params}`,
    { signal },
  )

  if (!response.ok) {
    const body = await response.json().catch(() => null)

    throw new Error(
      body?.error ?? "We couldn't load pull requests. Please try again.",
    )
  }

  return response.json()
}

export function RepositoryRow({
  repo,
  index,
}: {
  repo: ConnectedRepository
  index: number
}) {
  const [expanded, setExpanded] = useState(false)

  const reviewedPullRequests = 0; // TODO: `repo.reviewedPullRequests ?? 0`
  const reviewInProgress = false; // TODO: Boolean(repo.reviewInProgress)``
  const panelId = `repository-${repo.id}-pull-requests`;

  const pullRequestsQuery = useInfiniteQuery({
    queryKey: ["repository-pull-requests", repo.id],
    queryFn: ({ pageParam, signal }) =>
      fetchPullRequests({
        repositoryName: String(repo.name),
        page: pageParam,
        signal,
      }),
    initialPageParam: 1,
    retry: false,
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  const pullRequests =
    pullRequestsQuery.data?.pages.flatMap((page) => page.pullRequests) ?? []

  function submitForReview() {
    
  }

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: index * 0.04,
        duration: 0.2,
        ease: [0.32, 0.72, 0, 1],
      }}
      className="overflow-hidden rounded-xl border border-border/80 bg-background/75 shadow-sm backdrop-blur-sm transition-colors hover:border-border hover:bg-background"
    >
      <div className="flex items-center gap-3 p-3.5">
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={panelId}
          aria-label={`${expanded ? "Hide" : "Show"} pull requests for ${repo.name}`}
          onClick={() => setExpanded((value) => !value)}
          className="grid size-8 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronDown
            aria-hidden="true"
            size={17}
            className={`transition-transform duration-200 ${
              expanded ? "rotate-180" : ""
            }`}
          />
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {repo.name}
          </p>

          <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            {reviewInProgress ? (
              <>
                <LoaderCircle
                  aria-hidden="true"
                  size={13}
                  className="animate-spin text-blue-600 dark:text-blue-400"
                />
                <span className="text-blue-600 dark:text-blue-400">
                  Review in progress
                </span>
              </>
            ) : (
              <>
                <CheckCircle2 aria-hidden="true" size={13} />
                <span>Ready for review</span>
              </>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 border-l border-border pl-3">
          <GitPullRequest
            aria-hidden="true"
            size={16}
            className="hidden text-muted-foreground sm:block"
          />

          <div className="text-right">
            <p className="text-sm font-semibold tabular-nums text-foreground">
              {new Intl.NumberFormat().format(reviewedPullRequests)}
            </p>
            <p className="hidden text-[11px] text-muted-foreground sm:block">
              PRs reviewed
            </p>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={panelId}
            role="region"
            aria-label={`Open pull requests for ${repo.name}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              duration: 0.22,
              ease: [0.32, 0.72, 0, 1],
            }}
            className="overflow-hidden"
          >
            <div className="border-t border-border bg-muted/20 px-3.5 py-2 sm:px-4">
              {pullRequestsQuery.isPending ? (
                <div
                  role="status"
                  className="flex min-h-20 items-center justify-center gap-2 text-sm text-muted-foreground"
                >
                  <LoaderCircle
                    aria-hidden="true"
                    size={16}
                    className="animate-spin"
                  />
                  Loading pull requests…
                </div>
              ) : pullRequestsQuery.isError ? (
                <div className="flex min-h-20 flex-col items-center justify-center gap-2 text-center">
                  <p className="text-sm text-destructive">
                    {pullRequestsQuery.error instanceof Error
                      ? pullRequestsQuery.error.message
                      : "Pull requests could not be loaded."}
                  </p>

                  <button
                    type="button"
                    onClick={() => pullRequestsQuery.refetch()}
                    className="text-xs font-medium text-foreground underline underline-offset-4"
                  >
                    Try again
                  </button>
                </div>
              ) : pullRequests.length === 0 ? (
                <p className="py-5 text-center text-sm text-muted-foreground">
                  No open pull requests.
                </p>
              ) : (
                <>
                  <ul className="divide-y divide-border/70">
                    {pullRequests.map((pullRequest) => (
                      <li
                        key={`${repo.name}-${pullRequest.number}`}
                        className="flex justify-between py-1 first:pt-0 last:pb-0"
                      >
                        <div className="min-w-0">
                          <a
                            href={pullRequest.url}
                            target="_blank"
                            rel="noreferrer"
                            className="group/pr flex min-w-0 items-start gap-3"
                          >
                            <GitPullRequest
                              aria-hidden="true"
                              size={15}
                              className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                            />
                            <p className="wrap-break-word text-sm font-medium leading-5 text-foreground group-hover/pr:underline">
                              {pullRequest.title}
                            </p>
                            <ExternalLink
                              aria-hidden="true"
                              size={14}
                              className="mt-1 shrink-0 text-muted-foreground opacity-0 scale-50 group-hover/pr:opacity-100 group-hover/pr:scale-100 transition-[opacity,scale] duration-300"
                            />
                          </a>

                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                            <span>#{pullRequest.number}</span>

                            <span>
                              Updated{" "}
                              {new Intl.DateTimeFormat(undefined, {
                                dateStyle: "medium",
                              }).format(new Date(pullRequest.updatedAt))}
                            </span>
                          </div>
                        </div>

                        <Button
                          size="sm"
                          className="relative"
                          onClick={submitForReview}
                        >
                          review
                          <Send className="opacity-0"/>
                          <Send className="absolute right-2 top-1.45"/>
                        </Button>
                      </li>
                    ))}
                  </ul>

                  {pullRequestsQuery.hasNextPage && (
                    <div className="mt-3 border-t border-border/70 pt-3 text-center">
                      <button
                        type="button"
                        disabled={pullRequestsQuery.isFetchingNextPage}
                        onClick={() => pullRequestsQuery.fetchNextPage()}
                        className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-border bg-background px-3 text-xs font-medium text-foreground shadow-sm transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {pullRequestsQuery.isFetchingNextPage && (
                          <LoaderCircle
                            aria-hidden="true"
                            size={14}
                            className="animate-spin"
                          />
                        )}
                        {pullRequestsQuery.isFetchingNextPage
                          ? "Loading…"
                          : "Load more"}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  )
}
