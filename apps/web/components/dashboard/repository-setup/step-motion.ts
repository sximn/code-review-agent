import type { WizardDirection } from "./types"

export const STEP_TRANSITION = {
  duration: 0.28,
  ease: [0.32, 0.72, 0, 1],
} as const

export const STEP_VARIANTS = {
  enter: (direction: WizardDirection) => ({
    opacity: 0,
    x: direction * 56,
  }),
  center: {
    opacity: 1,
    x: 0,
  },
  exit: (direction: WizardDirection) => ({
    opacity: 0,
    x: direction * -40,
  }),
}
