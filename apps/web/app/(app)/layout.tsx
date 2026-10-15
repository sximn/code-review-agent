import { ReactNode } from "react";
import { SidebarShell } from "@/components/sidebar-shell";

export default function AppLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return <SidebarShell>{children}</SidebarShell>;
}
