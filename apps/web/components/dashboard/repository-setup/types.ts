export type RepositorySetupStep = 0 | 1 | 2

export type RepositoryCheckStatus = "idle" | "checking" | "success" | "error"

export type RepositoryCheckResult = {
  repository?: {
    fullName: string
  }
  error?: string
}

export type RepositorySaveResult = {
  error?: string
}

export type WizardDirection = 1 | -1
