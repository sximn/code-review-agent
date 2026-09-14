import FluidGradient from "@/components/fluid-gradient/fluid-gradient";

export default function Page() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="relative overflow-hidden flex flex-1 w-full flex-col items-center justify-end py-32 px-16 bg-white dark:bg-black sm:items-start">
        <FluidGradient
          intensity={1.55}
          lineCount={54}
          className="opacity-[0.92] brightness-100 dark:brightness-95"
        />

        <div className="relative z-10 mx-auto flex w-full max-w-360 flex-col px-5 sm:px-8 lg:px-12">
          <section id="top" className="flex flex-1 flex-col justify-center">
            <div className="max-w-4xl">

              <h1 className="max-w-4xl text-[clamp(3.7rem,10vw,9.5rem)] font-medium leading-[0.87] tracking-[-0.075em] text-slate-900 dark:text-white">
                <span className="bg-white dark:bg-gray-900">Verify</span>
                <br />
                <span className="text-[clamp(2.8rem,8vw,6rem)] font-medium bg-white/70 text-gray-600 dark:bg-gray-900/50 dark:text-white/85">before shipping.</span>
              </h1>

              <div className="mt-10 flex max-w-xl flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
                <p className="max-w-sm text-base leading-7 text-black dark:text-white/65 sm:text-lg">
                  Run automatic AI code review, gather insights & fix before you ship.
                </p>
                <a
                  href="/dashboard"
                  className="
                    group relative isolate inline-flex w-max shrink-0 items-center gap-3
                    overflow-hidden whitespace-nowrap rounded-full
                    border border-slate-200 bg-white px-5 py-3
                    text-sm font-semibold text-slate-900 shadow-sm
                    transition-[border-color,box-shadow,transform] duration-300
                    hover:border-slate-300 hover:shadow-md
                    focus-visible:outline-none focus-visible:ring-2
                    focus-visible:ring-slate-900 focus-visible:ring-offset-3
                    motion-reduce:transform-none motion-reduce:transition-none
                    dark:border-white/15 dark:bg-white/80 dark:text-black
                    dark:hover:border-white/25 dark:hover:bg-white/85
                  "
                >
                  <span>Start reviewing</span>

                  <span
                    aria-hidden="true"
                    className="
                      transition-transform duration-300
                      group-hover:translate-x-1 group-focus-visible:translate-x-1
                      motion-reduce:transform-none motion-reduce:transition-none
                    "
                  >
                    →
                  </span>
                </a>

              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
    
  );
}
