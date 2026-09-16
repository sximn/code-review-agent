import { useState } from "react"
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { AnimatePresence, motion } from "motion/react"
import {
  CheckCircle2,
  ChevronDown,
  CircleX,
  ExternalLink,
  GitPullRequest,
  LoaderCircle,
  Send,
} from "lucide-react"
import type { ConnectedRepository } from "@/lib/dashboard";
import type { PullRequest } from "@/lib/repositories";
import {
  createReviewResponseSchema,
  reviewsResponseSchema,
  type ReviewsResponse,
} from "@/lib/contracts/review";
import { Button } from "@/components/ui/button"
import z from "zod";

const PULL_REQUESTS_PER_PAGE = 25;

type PullRequestsPage = {
  pullRequests: PullRequest[];
  nextPage: number | null;
};

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

async function fetchReviews(
  repositoryName: string,
  signal?: AbortSignal,
): Promise<ReviewsResponse> {
  const params = new URLSearchParams({ repository: repositoryName })
  const response = await fetch(`/api/reviews?${params}`, { signal })

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error("Review statuses could not be loaded.")
  }

  const parsed = reviewsResponseSchema.safeParse(body)

  if (!parsed.success) {
    console.error("Invalid reviews API response", parsed.error);
    throw new Error("The reviews API returned an invalid response.");
  }

  return parsed.data;
}

async function createReview(
  repositoryName: string,
  pullRequestNumber: number,
) {
  const params = new URLSearchParams({
    repository: repositoryName,
    pullRequestNumber: String(pullRequestNumber),
  })
  const response = await fetch(`/api/reviews?${params}`, { method: "POST" })

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorResult = z
      .object({ error: z.string() })
      .safeParse(body);

    throw new Error(
      errorResult.success
        ? errorResult.data.error
        : "The review could not be started.",
    );
  }

  const parsed = createReviewResponseSchema.safeParse(body);

  if (!parsed.success) {
    console.error("Invalid create-review API response", parsed.error);
    throw new Error("The review API returned an invalid response.");
  }

  return parsed.data;
}


export function RepositoryRow({
  repo,
  index,
}: {
  repo: ConnectedRepository
  index: number
}) {
  const [expanded, setExpanded] = useState(false)
  const queryClient = useQueryClient()
  const panelId = `repository-${repo.id}-pull-requests`;

  const reviewsQuery = useQuery({
    queryKey: ["repository-reviews", repo.id],
    queryFn: ({ signal }) => fetchReviews(repo.name, signal),
    refetchInterval: (query) =>
      query.state.data?.reviews.some(
        (review) =>
          review.status === "scheduled" ||
          review.status === "running",
      ) 
        ? 2_000
        : false,
    });

  const createReviewMutation = useMutation({
    mutationFn: (pullRequestNumber: number) =>
      createReview(repo.name, pullRequestNumber),
    onSuccess: ({ review: createdReview }) => {
      queryClient.setQueryData<ReviewsResponse>(
        ["repository-reviews", repo.id],
        (current) => ({
          reviews: [
            createdReview,
            ...(current?.reviews.filter(
              (review) => review.id !== createdReview.id,
            ) ?? []),
          ],
        }),
      )
    },
  })

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
  const reviews = reviewsQuery.data?.reviews ?? []
  const reviewInProgress = reviewsQuery.data
    ? reviews.some(
        (review) => review.status === "scheduled" || review.status === "running",
      )
    : repo.reviewInProgress
  const reviewedPullRequests = repo.reviewedPullRequests

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
                    {pullRequests.map((pullRequest) => {
                      const latestReview = reviews.find(
                        (review) =>
                          review.pullRequestNumber === pullRequest.number,
                      )
                      const isStarting =
                        createReviewMutation.isPending &&
                        createReviewMutation.variables === pullRequest.number
                      const isActive =
                        latestReview?.status === "scheduled" ||
                        latestReview?.status === "running"

                      return <li
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
                          className="ml-3"
                          disabled={isStarting || isActive}
                          variant={latestReview?.status === "failed" ? "outline" : "default"}
                          onClick={() =>
                            createReviewMutation.mutate(pullRequest.number)
                          }
                        >
                          {isStarting || isActive ? (
                            <LoaderCircle className="animate-spin" />
                          ) : latestReview?.status === "finished" ? (
                            <CheckCircle2 />
                          ) : latestReview?.status === "failed" ? (
                            <CircleX />
                          ) : (
                            <Send />
                          )}
                          {isStarting
                            ? "Starting"
                            : latestReview?.status === "scheduled"
                              ? "Queued"
                              : latestReview?.status === "running"
                                ? "Reviewing"
                                : latestReview?.status === "finished"
                                  ? "Review again"
                                  : latestReview?.status === "failed"
                                    ? "Retry"
                                    : "Review"}
                        </Button>
                      </li>
                    })}
                  </ul>

                  {createReviewMutation.isError && (
                    <p className="mt-2 text-right text-xs text-destructive">
                      {createReviewMutation.error instanceof Error
                        ? createReviewMutation.error.message
                        : "The review could not be started."}
                    </p>
                  )}

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
