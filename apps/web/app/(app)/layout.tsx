import type { Metadata } from "next";
import { ReactNode } from "react";
import { SidebarShell } from "@/components/sidebar-shell";

export const metadata: Metadata = {
  title: "Simple Sandboxed Code Review",
  description: "Review your github PRs with AI",
};

export default function AppLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return <SidebarShell>{children}</SidebarShell>;
}
