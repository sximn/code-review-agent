import { ArrowLeft, ArrowRight, Check } from "lucide-react"
import { motion } from "motion/react"

import GithubLogo from "@/components/logos/github"
import { Button } from "@/components/ui/button"

import { STEP_TRANSITION, STEP_VARIANTS } from "./step-motion"
import type { WizardDirection } from "./types"

type AccessStepProps = {
  repository: string
  onBack: () => void
  onContinue: () => void
  direction: WizardDirection
}

export function AccessStep({
  repository,
  onBack,
  onContinue,
  direction,
}: AccessStepProps) {
  return (
    <motion.div
      custom={direction}
      variants={STEP_VARIANTS}
      initial="enter"
      animate="center"
      exit="exit"
      transition={STEP_TRANSITION}
    >
      <p className="text-sm font-medium text-muted-foreground">Step 2 of 3</p>
      <h3 className="mt-2 text-3xl font-semibold tracking-tighter text-foreground sm:text-4xl">
        Repository access
      </h3>
      <p className="mt-3 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">
        REWY needs read access to the repository and its pull request metadata.
      </p>

      <div className="mt-4 rounded-2xl border border-border/70 bg-background/65 p-5 shadow-sm backdrop-blur-sm">
        <div className="flex gap-4">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-background">
            <GithubLogo aria-hidden="true" size={20} />
          </div>
          <div className="min-w-0">
            <p className="font-medium text-foreground">{repository}</p>
            <p className="mt-1 text-sm leading-5 text-muted-foreground">
              This public repository was verified with GitHub. Private repository support is not available yet.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <AccessPermission label="Read repository metadata" />
        <AccessPermission label="Read pull requests" />
        <AccessPermission label="Read changed files and diffs" />
      </div>

      <div className="mt-8 flex items-center justify-between gap-3">
        <Button type="button" variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft aria-hidden="true" size={16} />
          Back
        </Button>
        <Button type="button" onClick={onContinue} className="gap-2">
          Continue
          <ArrowRight aria-hidden="true" size={16} />
        </Button>
      </div>
    </motion.div>
  )
}

function AccessPermission({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="grid size-5 shrink-0 place-items-center rounded-full bg-foreground text-background">
        <Check aria-hidden="true" size={12} strokeWidth={3} />
      </span>
      <span className="text-foreground/85">{label}</span>
    </div>
  )
}
