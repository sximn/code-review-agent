"use client";

import { createContext, useContext, type ReactNode } from "react";

export type EnvironmentFlags = {
  isDev: boolean;
  isProd: boolean;
};

const EnvironmentContext = createContext<EnvironmentFlags | null>(null);

export function EnvironmentProvider({
  value,
  children,
}: {
  value: EnvironmentFlags;
  children: ReactNode;
}) {
  return (
    <EnvironmentContext.Provider value={value}>
      {children}
    </EnvironmentContext.Provider>
  );
}

export function useEnv() {
  const context = useContext(EnvironmentContext);

  if (context === null) {
    throw new Error("useEnv must be used inside EnvironmentProvider");
  }

  return context;
}
