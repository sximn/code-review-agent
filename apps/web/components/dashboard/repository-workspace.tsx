import { ArrowRight, CheckCircle2, Code2, GitPullRequest, LoaderCircle } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { Button } from "@/components/ui/button"

import { RepositorySetupWizard } from "./repository-setup/repository-setup-wizard"
import { ConnectedRepository } from "@/lib/dashboard"

type RepositoryWorkspaceProps = {
  isEmpty: boolean
  configuring: boolean
  repository: string
  connectedRepositories: ConnectedRepository[]
  setRepository: (repository: string) => void
  onConfigure: () => void
  onClose: () => void
  onComplete: () => void
}

export function RepositoryWorkspace({
  isEmpty,
  configuring,
  repository,
  connectedRepositories,
  setRepository,
  onConfigure,
  onClose,
  onComplete,
}: RepositoryWorkspaceProps) {
  return (
    <motion.section
      layout
      id="repository-setup"
      aria-labelledby={
        configuring ? "repository-setup-heading" : "review-space-heading"
      }
      className={[
        "relative isolate mx-auto mt-4 w-full max-w-260 h-fit overflow-hidden rounded-[15px] border border-border",
        "bg-[linear-gradient(135deg,#f4f8ff,#fff_52%,#f3f7ff)]",
        "dark:bg-[linear-gradient(135deg,#070d1a,#0d121f_52%,#060914)]",
        "dark:shadow-[0_16px_40px_rgba(0,0,0,0.25)]",
        configuring
          ? "min-h-[min(620px,calc(100vh-7rem))]"
          : "min-h-105",
      ].join(" ")}
      style={{ transformOrigin: "center bottom" }}
    >
      <WorkspaceBackground configuring={configuring} />

      <AnimatePresence initial={false} mode="wait">
        {!configuring ? (
          isEmpty 
            ? <EmptyRepositoryState key="empty" onConfigure={onConfigure} />
            : <ConnectedRepositories key="repos" repositories={connectedRepositories} />
          
        ) : (
          <RepositorySetupWizard
            key="setup"
            repository={repository}
            setRepository={setRepository}
            onClose={onClose}
            onComplete={onComplete}
          />
        )}
      </AnimatePresence>
    </motion.section>
  )
}

function WorkspaceBackground({ configuring }: { configuring: boolean }) {
  return (
    <>
      <motion.div
        aria-hidden="true"
        animate={{ opacity: configuring ? 0.13 : 0.55, scale: configuring ? 1.035 : 1 }}
        transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(#dce6f5_1px,transparent_1px),linear-gradient(90deg,#dce6f5_1px,transparent_1px)] bg-size-[45px_45px] mask-[linear-gradient(transparent,black_30%,black_65%,transparent)] dark:bg-[linear-gradient(#263753_1px,transparent_1px),linear-gradient(90deg,#263753_1px,transparent_1px)]"
      />
      <motion.div
        aria-hidden="true"
        animate={{
          opacity: configuring ? 0 : 0.5,
          x: configuring ? -50 : 0,
          y: configuring ? 40 : 0,
          scale: configuring ? 1.08 : 1,
        }}
        transition={{ duration: 0.45, ease: [0.32, 0.72, 0, 1] }}
        className="pointer-events-none absolute -bottom-45 -left-31.25 size-87.5 rounded-full border border-[#bdd2f8] dark:border-[#29466f]"
      />
      <motion.div
        aria-hidden="true"
        animate={{
          opacity: configuring ? 0 : 0.5,
          x: configuring ? 50 : 0,
          y: configuring ? -40 : 0,
          scale: configuring ? 1.08 : 1,
        }}
        transition={{ duration: 0.45, ease: [0.32, 0.72, 0, 1] }}
        className="pointer-events-none absolute -right-35 -top-42.5 size-87.5 rounded-full border border-[#bdd2f8] dark:border-[#29466f]"
      />
    </>
  )
}

function EmptyRepositoryState({
  onConfigure,
}: {
  onConfigure: () => void
}) {
  return (
    <motion.div
      layout
      initial={false}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -18, scale: 0.985 }}
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      className="absolute inset-0 grid place-items-center"
    >
      <motion.div layout="position" className="relative flex max-w-md flex-col items-center p-7.5 text-center">
        <div className="grid size-10 place-items-center rounded-xl border border-border bg-background text-foreground shadow-sm">
          <Code2 aria-hidden="true" size={24} strokeWidth={2.25} />
        </div>
        <h2 id="review-space-heading" className="mt-2 text-2xl font-medium tracking-[-0.055em] text-foreground sm:text-3xl">
          Nothing reviewed yet.
        </h2>
        <p className="mt-2 max-w-sm text-sm leading-5 text-muted-foreground">
          Connect a repository and REWY will start looking for what your team might miss.
        </p>
        
        <Button type="button" onClick={onConfigure} variant="outline" size="lg" className="group mt-7 gap-2">
          Set up your first repository
          <ArrowRight aria-hidden="true" size={17} className="transition-transform duration-200 group-hover:translate-x-0.5" />
        </Button>
      </motion.div>
    </motion.div>
  )
}

function ConnectedRepositories({
  repositories,
}: {
  repositories: ConnectedRepository[]
}) {
  return (
    <motion.div
      layout
      initial={false}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -18, scale: 0.985 }}
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      className="absolute inset-0 overflow-y-auto"
    >
      <motion.div
        layout="position"
        className="mx-auto flex w-full max-w-3xl flex-col p-5 sm:p-7"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="review-space-heading"
              className="mt-1 text-xl font-medium tracking-[-0.055em] text-foreground sm:text-2xl"
            >
              Connected repositories
            </h2>

            <p className="mt-1.5 text-sm leading-5 text-muted-foreground">
              Review activity across the repositories connected to REWY.
            </p>
          </div>

          <div className="shrink-0 rounded-full border border-border bg-background/70 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-sm">
            {repositories.length}{" "}
            {repositories.length === 1 ? "repository" : "repositories"}
          </div>
        </div>

        <motion.ul layout className="mt-3 grid gap-3">
          {repositories.map((repo, index) => {
            const reviewedPullRequests = 0;// TODO: `repo.reviewedPullRequests ?? 0`
            const reviewInProgress = false // TODO: `Boolean(repo.reviewInProgress)`

            return (
              <motion.li
                key={repo.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: index * 0.04,
                  duration: 0.2,
                  ease: [0.32, 0.72, 0, 1],
                }}
                className="group flex items-center gap-3 rounded-xl border border-border/80 bg-background/75 p-3.5 shadow-sm backdrop-blur-sm transition-colors hover:border-border hover:bg-background"
              >
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
                    className="text-muted-foreground"
                  />

                  <div className="text-right">
                    <p className="text-sm font-semibold tabular-nums text-foreground">
                      {new Intl.NumberFormat().format(reviewedPullRequests)}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      PRs reviewed
                    </p>
                  </div>
                </div>
              </motion.li>
            )
          })}
        </motion.ul>
      </motion.div>
    </motion.div>
  )
}