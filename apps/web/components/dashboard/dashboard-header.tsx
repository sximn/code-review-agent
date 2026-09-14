import { ArrowRight, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"

const GREETINGS = [
  (name: string) => `Good to see you, ${name}.`,
  (name: string) => `Welcome back, ${name}.`,
  (name: string) => `Ready when you are, ${name}.`,
  (name: string) => `Let's make progress, ${name}.`,
  (name: string) => `Here's what's happening, ${name}.`,
  (name: string) => `Your workspace is ready, ${name}.`,
  (name: string) => `Time to build, ${name}.`,
  (name: string) => `Let's get after it, ${name}.`,
  (name: string) => `Another great day to ship, ${name}.`,
  (name: string) => `What are we tackling today, ${name}?`,
  (name: string) => `Back in action, ${name}.`,
  (name: string) => `Let's make something happen, ${name}.`,
  (name: string) => `Your next move starts here, ${name}.`,
  (name: string) => `All systems ready, ${name}.`,
  (name: string) => `Let's keep things moving, ${name}.`,
  (name: string) => `You've got this, ${name}.`,
  (name: string) => `Ready to make an impact, ${name}?`,
  (name: string) => `One step closer, ${name}.`,
  (name: string) => `Let's turn ideas into action, ${name}.`,
  (name: string) => `Welcome to your command center, ${name}.`,
]

function getGreeting(name: string): string {
  const today = new Date().toISOString().slice(0, 10)
  let seed = 0

  for (const character of today) {
    seed = (seed * 31 + character.charCodeAt(0)) >>> 0
  }

  return GREETINGS[seed % GREETINGS.length](name)
}

type DashboardHeaderProps = {
  isEmpty: boolean
  userName: string
  onConfigure: () => void
}

export function DashboardHeader({
  isEmpty,
  userName,
  onConfigure,
}: DashboardHeaderProps) {
  return (
    <section
      className="flex flex-col gap-8 pb-5 sm:pb-6 lg:flex-row lg:items-end lg:justify-between"
      aria-labelledby="dashboard-heading"
    >
      <div>
        <h1
          id="dashboard-heading"
          className="text-2xl font-semibold tracking-[-0.055em] text-foreground sm:text-3xl"
        >
          Dashboard
        </h1>

        <p className="mt-1 text-lg text-foreground/80 sm:text-xl">
          {isEmpty
            ? `Whenever you are ready, ${userName}.`
            : getGreeting(userName)}
        </p>

        <p className="mt-1 text-sm text-muted-foreground sm:text-base">
          {isEmpty
            ? "Your codebase is quiet. That's a good place to start."
            : "Here is what your team has caught this week."}
        </p>
      </div>

      <Button
        type="button"
        onClick={onConfigure}
        className="group max-w-sm gap-2"
      >
        <Plus
          aria-hidden="true"
          size={18}
          className="transition-transform duration-300 group-hover:rotate-90"
        />
        Configure repository
        <ArrowRight aria-hidden="true" size={18} />
      </Button>
    </section>
  )
}
