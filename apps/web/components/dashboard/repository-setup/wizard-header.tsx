import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

import { SetupProgress } from "./setup-progress";
import type { RepositorySetupStep } from "./types";

type WizardHeaderProps = {
  step: RepositorySetupStep;
  onClose: () => void;
  isBusy: boolean;
};

export function WizardHeader({ step, onClose, isBusy }: WizardHeaderProps) {
  return (
    <>
      <div className="relative z-10 flex items-start justify-between gap-6 border-b border-border/60 px-5 py-5 sm:items-center sm:px-8">
        <div>
          <h2
            id="repository-setup-heading"
            className="text-sm font-medium text-foreground"
          >
            Configure repository
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">
            Connect a codebase for automated review.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:block">
            <SetupProgress step={step} />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            disabled={isBusy}
            className="rounded-full"
            aria-label="Close repository setup"
          >
            <X aria-hidden="true" size={18} />
          </Button>
        </div>
      </div>

      <div className="relative z-10 border-b border-border/60 px-5 py-3 md:hidden">
        <SetupProgress step={step} />
      </div>
    </>
  );
}
