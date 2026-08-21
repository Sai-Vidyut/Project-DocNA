import type { ReactNode } from "react"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[calc(100vh-var(--header-height))] overflow-x-hidden">{children}</div>
  )
}
