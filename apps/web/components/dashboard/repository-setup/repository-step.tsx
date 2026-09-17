import { ArrowRight, CheckCircle2, LoaderCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import GithubLogo from "@/components/logos/github";
import { Button } from "@/components/ui/button";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Label } from "@/components/ui/label";

import { STEP_TRANSITION, STEP_VARIANTS } from "./step-motion";
import type { RepositoryCheckStatus, WizardDirection } from "./types";

type RepositoryStepProps = {
  repository: string;
  onRepositoryChange: (value: string) => void;
  status: RepositoryCheckStatus;
  error: string | null;
  onContinue: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  direction: WizardDirection;
};

export function RepositoryStep({
  repository,
  onRepositoryChange,
  status,
  error,
  onContinue,
  inputRef,
  direction,
}: RepositoryStepProps) {
  const isChecking = status === "checking";
  const isSuccess = status === "success";
  const isError = status === "error";

  return (
    <motion.div
      custom={direction}
      variants={STEP_VARIANTS}
      initial="enter"
      animate="center"
      exit="exit"
      transition={STEP_TRANSITION}
    >
      <p className="text-sm font-medium text-muted-foreground">Step 1 of 3</p>
      <h3 className="mt-2 max-w-lg text-3xl font-semibold tracking-tighter text-foreground sm:text-4xl">
        Which repository should REWY review?
      </h3>
      <p className="mt-3 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">
        Enter the GitHub repository using the{" "}
        <span className="font-medium text-foreground">owner/repository</span>{" "}
        format.
      </p>

      <form
        className="mt-2"
        onSubmit={(event) => {
          event.preventDefault();
          onContinue();
        }}
      >
        <Label htmlFor="repository">GitHub repository</Label>
        <InputGroup className="mt-2">
          <InputGroupInput
            id="repository"
            ref={inputRef}
            value={repository}
            disabled={isChecking}
            onChange={(event) => onRepositoryChange(event.target.value)}
            aria-describedby={isError ? "repository-error" : undefined}
            aria-invalid={isError || undefined}
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder="owner/repo"
          />
          <InputGroupAddon>
            <GithubLogo
              aria-hidden="true"
              size={18}
              className="text-muted-foreground"
            />
          </InputGroupAddon>
        </InputGroup>

        <AnimatePresence initial={false}>
          {isChecking && (
            <motion.div
              key="checking"
              initial={{ opacity: 0, height: 0, y: -4 }}
              animate={{ opacity: 1, height: "auto", y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div
                role="status"
                aria-live="polite"
                className="mt-3 flex items-center gap-2 text-sm text-muted-foreground"
              >
                <LoaderCircle
                  aria-hidden="true"
                  size={16}
                  className="animate-spin"
                />
                Checking repository and pull request access...
              </div>
            </motion.div>
          )}

          {isSuccess && (
            <motion.div
              key="success"
              initial={{ opacity: 0, height: 0, y: -4 }}
              animate={{ opacity: 1, height: "auto", y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div
                role="status"
                aria-live="polite"
                className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-500/6 p-4"
              >
                <div className="flex gap-3">
                  <CheckCircle2
                    aria-hidden="true"
                    size={18}
                    className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                  />
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Repository found
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      We can reach this public repository.
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {isError && (
            <motion.div
              key="error"
              initial={{ opacity: 0, height: 0, y: -4 }}
              animate={{ opacity: 1, height: "auto", y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div
                id="repository-error"
                role="alert"
                className="mt-3 rounded-xl border border-destructive/20 bg-destructive/4.5 p-4"
              >
                <p className="text-sm font-medium text-foreground">
                  We couldn&apos;t access this repository.
                </p>
                <p className="mt-1 text-sm leading-5 text-muted-foreground">
                  {error ??
                    "Check the repository name. Private repositories aren't available yet."}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-2 flex justify-end">
          <Button
            type="submit"
            disabled={!repository.trim() || isChecking}
            className="min-w-31 gap-2"
          >
            {isChecking ? (
              <>
                <LoaderCircle
                  aria-hidden="true"
                  size={16}
                  className="animate-spin"
                />
                Checking
              </>
            ) : isSuccess ? (
              <>
                Continue
                <ArrowRight aria-hidden="true" size={16} />
              </>
            ) : (
              <>
                Check repository
                <ArrowRight aria-hidden="true" size={16} />
              </>
            )}
          </Button>
        </div>
      </form>
    </motion.div>
  );
}
