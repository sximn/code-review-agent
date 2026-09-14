"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "motion/react"
import { toast } from "sonner"

import { isRepositoryName, normalizeRepository } from "@/lib/repository-name"

import { AccessStep } from "./access-step"
import { ConfigurationStep } from "./configuration-step"
import { RepositoryStep } from "./repository-step"
import type {
  RepositoryCheckResult,
  RepositoryCheckStatus,
  RepositorySaveResult,
  RepositorySetupStep,
  WizardDirection,
} from "./types"
import { WizardHeader } from "./wizard-header"

type RepositorySetupWizardProps = {
  repository: string
  setRepository: (repository: string) => void
  onClose: () => void
  onComplete: () => void
}

export function RepositorySetupWizard({
  repository,
  setRepository,
  onClose,
  onComplete,
}: RepositorySetupWizardProps) {
  const router = useRouter()
  const [step, setStep] = React.useState<RepositorySetupStep>(0)
  const [direction, setDirection] = React.useState<WizardDirection>(1)
  const [checkStatus, setCheckStatus] = React.useState<RepositoryCheckStatus>("idle")
  const [checkError, setCheckError] = React.useState<string | null>(null)
  const [isSaving, setIsSaving] = React.useState(false)
  const [saveError, setSaveError] = React.useState<string | null>(null)
  const repositoryInputRef = React.useRef<HTMLInputElement>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)

  React.useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  React.useEffect(() => {
    if (step !== 0) {
      return
    }

    const frame = requestAnimationFrame(() => repositoryInputRef.current?.focus())
    return () => cancelAnimationFrame(frame)
  }, [step])

  React.useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !isSaving) {
        onClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isSaving, onClose])

  function goToStep(nextStep: RepositorySetupStep, nextDirection: WizardDirection) {
    setDirection(nextDirection)
    setStep(nextStep)
  }

  function handleRepositoryChange(value: string) {
    setRepository(value)
    setCheckStatus("idle")
    setCheckError(null)
  }

  async function checkRepository() {
    const normalizedRepository = normalizeRepository(repository)

    if (!isRepositoryName(normalizedRepository)) {
      setCheckStatus("error")
      setCheckError("Enter a repository in owner/repository format.")
      return
    }

    setRepository(normalizedRepository)

    if (checkStatus === "success") {
      goToStep(1, 1)
      return
    }

    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    setCheckStatus("checking")
    setCheckError(null)

    try {
      const response = await fetch("/api/repositories/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ repository: normalizedRepository }),
        signal: controller.signal,
      })
      const data = (await response.json().catch(() => null)) as RepositoryCheckResult | null

      if (!response.ok) {
        setCheckStatus("error")
        setCheckError(
          data?.error ??
            "We couldn't reach that repository. Check the name; private repositories aren't available yet.",
        )
        return
      }

      if (!data?.repository) {
        setCheckStatus("error")
        setCheckError("We couldn't verify that repository. Please try again.")
        return
      }

      setRepository(data.repository.fullName)
      setCheckStatus("success")
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return
      }

      setCheckStatus("error")
      setCheckError("Something went wrong while checking the repository. Please try again.")
    }
  }

  async function handleFinish() {
    setIsSaving(true)
    setSaveError(null)

    try {
      const response = await fetch("/api/repositories", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ repository }),
      })
      const data = (await response.json().catch(() => null)) as RepositorySaveResult | null

      if (!response.ok) {
        setSaveError(data?.error ?? "We couldn't connect this repository. Please try again.")
        return
      }

      onComplete()
      toast.success("Repository connected")
      router.refresh()
    } catch {
      setSaveError("We couldn't connect this repository. Please try again.")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 26, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 18, scale: 0.99 }}
      transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
      className="relative flex min-h-[min(620px,calc(100vh-7rem))] flex-col"
    >
      <WizardHeader step={step} onClose={onClose} isBusy={isSaving} />

      <div className="relative z-10 flex flex-1 items-center justify-center overflow-hidden px-5 py-10 sm:px-10 sm:py-14 lg:px-14">
        <div className="w-full max-w-xl">
          <AnimatePresence custom={direction} initial={false} mode="wait">
            {step === 0 && (
              <RepositoryStep
                key="repository"
                repository={repository}
                onRepositoryChange={handleRepositoryChange}
                status={checkStatus}
                error={checkError}
                onContinue={checkRepository}
                inputRef={repositoryInputRef}
                direction={direction}
              />
            )}
            {step === 1 && (
              <AccessStep
                key="access"
                repository={repository}
                onBack={() => goToStep(0, -1)}
                onContinue={() => goToStep(2, 1)}
                direction={direction}
              />
            )}
            {step === 2 && (
              <ConfigurationStep
                key="configuration"
                repository={repository}
                onBack={() => goToStep(1, -1)}
                onFinish={handleFinish}
                isSaving={isSaving}
                saveError={saveError}
                direction={direction}
              />
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}
