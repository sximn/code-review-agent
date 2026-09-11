"use client"

import { QueryClientProvider } from "@tanstack/react-query"
import Link from "next/link"
import { useTheme } from "next-themes"
import { useParams, useRouter } from "next/navigation"
import type { ReactNode } from "react"
import { authClient } from "@/lib/auth-client"
import { getQueryClient } from "@/lib/query-client"
import { AuthProvider } from "./auth/auth-provider"
import { Toaster } from "./ui/sonner"
import { usernamePlugin } from "@better-auth-ui/core/plugins/username"
import { magicLinkPlugin } from "@better-auth-ui/core/plugins/magic-link"
import { passkeyPlugin } from "@better-auth-ui/core/plugins/passkey"
import { multiSessionPlugin } from "@better-auth-ui/core/plugins/multi-session"
import { organizationPlugin } from "@better-auth-ui/core/plugins/organization"
import { themePlugin } from "@/lib/auth/theme-plugin"
import { deleteUserPlugin } from "@/lib/auth/delete-user-plugin"

const normalizeParam = (param: string | string[] | undefined) =>
  (Array.isArray(param) ? param[0] : param)?.replace(/^@/, "") ?? null

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter()
  const params = useParams()
  const queryClient = getQueryClient()
  const slug = normalizeParam(params.slug)

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        authClient={authClient}
        redirectTo="/settings/account"
        socialProviders={["google", "github"]}
        emailAndPassword={{ enabled: false, requireEmailVerification: false }}
        navigate={({ to, replace }) =>
          replace ? router.replace(to) : router.push(to)
        }
        plugins={[
          usernamePlugin({
            usernamePrefix: "@",
            localization: { usernamePlaceholder: "username" }
          }),
          magicLinkPlugin(),
          passkeyPlugin(),
          themePlugin({ useTheme }),
          multiSessionPlugin(),
          deleteUserPlugin(),
          organizationPlugin({
            slugPrefix: "@",
            slug
          })
        ]}
        Link={Link}
      >
        {children}

        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  )
}
