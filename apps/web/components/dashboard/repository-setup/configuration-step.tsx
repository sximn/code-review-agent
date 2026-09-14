import { ArrowLeft, Check, CheckCircle2, LoaderCircle } from "lucide-react"
import { motion } from "motion/react"

import GithubLogo from "@/components/logos/github"
import { Button } from "@/components/ui/button"

import { STEP_TRANSITION, STEP_VARIANTS } from "./step-motion"
import type { WizardDirection } from "./types"

type ConfigurationStepProps = {
  repository: string
  onBack: () => void
  onFinish: () => Promise<void>
  isSaving: boolean
  saveError: string | null
  direction: WizardDirection
}

export function ConfigurationStep({
  repository,
  onBack,
  onFinish,
  isSaving,
  saveError,
  direction,
}: ConfigurationStepProps) {
  return (
    <motion.div
      custom={direction}
      variants={STEP_VARIANTS}
      initial="enter"
      animate="center"
      exit="exit"
      transition={STEP_TRANSITION}
    >
      <p className="text-sm font-medium text-muted-foreground">Step 3 of 3</p>
      <h3 className="mt-2 text-3xl font-semibold tracking-tighter text-foreground sm:text-4xl">
        Ready to connect.
      </h3>
      <p className="mt-3 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">
        Review the repository before adding it to your workspace.
      </p>

      <div className="mt-8 overflow-hidden rounded-2xl border border-border/70 bg-background/65 shadow-sm backdrop-blur-sm">
        <div className="flex items-center gap-4 border-b border-border/60 p-5">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-background">
            <GithubLogo aria-hidden="true" size={20} />
          </div>
          <div className="min-w-0">
            <p className="font-medium text-foreground">{repository}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">GitHub repository</p>
          </div>
          <CheckCircle2
            aria-hidden="true"
            size={19}
            className="ml-auto shrink-0 text-emerald-600 dark:text-emerald-400"
          />
        </div>

        <div className="grid gap-px bg-border/60 sm:grid-cols-2">
          <div className="bg-background/80 p-5">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-muted-foreground">Repository</p>
            <p className="mt-2 text-sm font-medium text-foreground">Public access verified</p>
          </div>
          <div className="bg-background/80 p-5">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-muted-foreground">Connection</p>
            <p className="mt-2 text-sm font-medium text-foreground">Ready to add to your workspace</p>
          </div>
        </div>
      </div>

      {saveError && (
        <div role="alert" className="mt-4 rounded-xl border border-destructive/20 bg-destructive/4.5 p-4 text-sm text-muted-foreground">
          {saveError}
        </div>
      )}

      <div className="mt-8 flex items-center justify-between gap-3">
        <Button type="button" variant="ghost" onClick={onBack} disabled={isSaving} className="gap-2">
          <ArrowLeft aria-hidden="true" size={16} />
          Back
        </Button>
        <Button type="button" onClick={() => void onFinish()} disabled={isSaving} className="gap-2">
          {isSaving ? (
            <><LoaderCircle aria-hidden="true" size={16} className="animate-spin" />Connecting</>
          ) : (
            <><Check aria-hidden="true" size={16} />Connect repository</>
          )}
        </Button>
      </div>
    </motion.div>
  )
}
