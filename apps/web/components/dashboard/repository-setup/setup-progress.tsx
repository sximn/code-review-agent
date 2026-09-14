import * as React from "react"
import { Check, LockKeyhole, Settings2 } from "lucide-react"

import GithubLogo from "@/components/logos/github"

import type { RepositorySetupStep } from "./types"

const SETUP_STEPS = [
  { label: "Repository", icon: GithubLogo },
  { label: "Access", icon: LockKeyhole },
  { label: "Configure", icon: Settings2 },
] as const

export function SetupProgress({ step }: { step: RepositorySetupStep }) {
  return (
    <div className="flex items-center gap-2">
      {SETUP_STEPS.map((item, index) => {
        const Icon = item.icon
        const isComplete = index < step
        const isActive = index === step

        return (
          <React.Fragment key={item.label}>
            {index > 0 && (
              <div
                className={[
                  "hidden h-px w-7 transition-colors duration-300 sm:block",
                  index <= step ? "bg-foreground/30" : "bg-border",
                ].join(" ")}
              />
            )}
            <div
              aria-current={isActive ? "step" : undefined}
              aria-label={`${item.label}, ${
                isComplete ? "complete" : isActive ? "current" : "upcoming"
              }`}
              className={[
                "flex items-center gap-2 rounded-full px-2.5 py-1.5 text-xs transition-colors duration-300 sm:text-sm",
                isActive
                  ? "bg-foreground text-background"
                  : isComplete
                    ? "bg-foreground/[0.07] text-foreground"
                    : "text-muted-foreground",
              ].join(" ")}
            >
              <span className="grid size-5 place-items-center">
                {isComplete ? (
                  <Check aria-hidden="true" size={14} strokeWidth={2.5} />
                ) : (
                  <Icon aria-hidden="true" size={14} />
                )}
              </span>
              <span className="hidden sm:inline">{item.label}</span>
            </div>
          </React.Fragment>
        )
      })}
    </div>
  )
}
