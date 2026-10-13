"use client";

import { useEffect, useId, useState, type ReactNode } from "react";
import { ChevronsLeftRightEllipsis, Home, LibraryBig } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Logo } from "./logo";
import { UserButton } from "./auth/user/user-button";

const items = [
  { label: "Overview", href: "/dashboard", icon: Home },
  { label: "Repositories", href: "/repositories", icon: LibraryBig },
  { label: "Reviews", href: "/reviews", icon: ChevronsLeftRightEllipsis },
];

type Props = {
  children: ReactNode;
};

export function SidebarShell({ children }: Props) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const mobileMenuId = useId();

  // Close a mobile drawer if the viewport switches to desktop.
  // Keep this query aligned with Tailwind's md breakpoint.
  useEffect(() => {
    const query = window.matchMedia("(min-width: 768px)");
    const onChange = () => {
      if (query.matches) setMobileOpen(false);
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  function navigation(mobile = false) {
    return (
      <nav aria-label="Main navigation" className="space-y-1">
        {items.map(({ label, href, icon: Icon }) => {
          const active = pathname === href;

          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              aria-current={active ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "relative flex w-full items-center overflow-hidden rounded-md",
                "text-sm text-accent-foreground",
                "transition-colors duration-150",
                "hover:bg-muted hover:text-accent-foreground dark:hover:bg-muted/50",
                "focus-visible:ring-2 focus-visible:outline-none",
                "focus-visible:ring-ring focus-visible:ring-inset",
                active && "bg-muted text-accent-foreground",
              )}
            >
              <span className="flex size-9 shrink-0 items-center justify-center">
                <Icon className="size-5" aria-hidden="true" />
              </span>

              <span
                className={cn(
                  "absolute left-12 whitespace-nowrap",
                  !mobile && [
                    "opacity-0 transition-opacity duration-150 ease-out",
                    "group-hover:opacity-100 group-hover:delay-75",
                    "group-has-focus-visible:opacity-100 group-has-focus-visible:delay-75",
                    "motion-reduce:transition-none motion-reduce:delay-0",
                  ],
                )}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <div className="min-h-dvh bg-background text-foreground">
      {/* fixed panel: growing its width never changes the content offset */}
      <aside
        className={cn(
          "group fixed inset-y-0 left-0 z-40 hidden w-15",
          "overflow-hidden border-r bg-background md:block",
          "transition-[width,box-shadow] duration-200 ease-out",
          "hover:w-64 hover:shadow-xl",
          "has-focus-visible:w-64 has-focus-visible:shadow-xl",
          "motion-reduce:transition-none",
        )}
      >
        <div className="flex h-full w-full flex-col p-3">
          <div className="flex h-12 shrink-0 items-center border-b">
            <Link href="/" className="flex items-center gap-2.5 no-underline">
              <Logo />

              <h1 className="text-base">REWY.</h1>
            </Link>
          </div>

          <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
            {navigation()}
          </div>

          <UserButton className="px-1 py-2" />
        </div>
      </aside>

      {/* constant offset prevents dashboard movement on hover */}
      <div className="md:pl-17">
        <header className="sticky top-0 z-30 border-b bg-background md:hidden">
          <div className="relative grid grid-cols-[1fr_auto_1fr] items-center px-4 py-1">
            <Button
              variant="ghost"
              size="icon"
              className="justify-self-start hover:bg-transparent hover:text-foreground aria-expanded:bg-transparent dark:hover:bg-transparent"
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileOpen}
              aria-controls={mobileMenuId}
              onClick={() => setMobileOpen((open) => !open)}
            >
              {/* 3 lines animate into X */}
              <span className="relative block size-5" aria-hidden="true">
                <span
                  className={cn(
                    "absolute top-1/2 left-0 h-0.5 w-5 rounded-full bg-current",
                    "transition-transform duration-200 motion-reduce:transition-none",
                    mobileOpen
                      ? "-translate-y-1/2 rotate-45"
                      : "-translate-y-1.75",
                  )}
                />
                <span
                  className={cn(
                    "absolute top-1/2 left-0 h-0.5 w-5 -translate-y-1/2 rounded-full bg-current",
                    "transition-opacity duration-150 motion-reduce:transition-none",
                    mobileOpen ? "opacity-0" : "opacity-100",
                  )}
                />
                <span
                  className={cn(
                    "absolute top-1/2 left-0 h-0.5 w-5 rounded-full bg-current",
                    "transition-transform duration-200 motion-reduce:transition-none",
                    mobileOpen
                      ? "-translate-y-1/2 -rotate-45"
                      : "translate-y-1.25",
                  )}
                />
              </span>
            </Button>

            <Link href="/" className="flex items-center gap-2.5 no-underline">
              <Logo className="size-6" />
              <span className="text-base">REWY.</span>
            </Link>

            <div className="justify-self-end">
              <UserButton size="icon" />
            </div>
          </div>

          <div
            id={mobileMenuId}
            inert={!mobileOpen}
            aria-hidden={!mobileOpen}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setMobileOpen(false);
                document
                  .querySelector<HTMLButtonElement>(
                    `button[aria-controls="${mobileMenuId}"]`,
                  )
                  ?.focus();
              }
            }}
            className={cn(
              "absolute inset-x-0 top-full grid bg-background shadow-lg",
              "transition-[grid-template-rows,opacity] duration-200 ease-out",
              "motion-reduce:transition-none",
              mobileOpen
                ? "grid-rows-[1fr] opacity-100"
                : "grid-rows-[0fr] opacity-0",
            )}
          >
            <div className="min-h-0 overflow-hidden">
              <div className="max-h-[70dvh] overflow-y-auto border py-3">
                {navigation(true)}
              </div>
            </div>
          </div>
        </header>

        <main className="min-w-0 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
