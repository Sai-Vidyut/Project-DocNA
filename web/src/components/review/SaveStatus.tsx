import type { AutosaveStatus } from "@/lib/use-autosave"

interface SaveStatusProps {
  status: AutosaveStatus
  lastSavedAt: Date | null
  pendingInputCount: number
}

function formatSavedAt(date: Date | null): string {
  if (!date) return "Saved"
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 8) return "Saved just now"
  if (seconds < 60) return `Saved ${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  return `Saved ${minutes}m ago`
}

export function SaveStatus({ status, lastSavedAt, pendingInputCount }: SaveStatusProps) {
  let message = "Changes save automatically"
  let dotClass = "status-dot status-dot--saved opacity-40"

  if (status === "saving") {
    message = "Saving…"
    dotClass = "status-dot status-dot--saving"
  } else if (status === "error") {
    message = "Could not save — keep editing to retry"
    dotClass = "status-dot status-dot--error"
  } else if (status === "saved") {
    message = formatSavedAt(lastSavedAt)
    dotClass = "status-dot status-dot--saved"
  }

  return (
    <div className="export-finish">
      <div className="workspace-divider mb-4" aria-hidden />
      <div className="flex items-center gap-2" aria-live="polite">
        <span className={dotClass} aria-hidden />
        <p className="m-0 text-[0.8125rem] text-[hsl(var(--muted))]">{message}</p>
      </div>
      {pendingInputCount > 0 ? (
        <p className="mt-1.5 mb-0 type-meta">
          Complete {pendingInputCount} remaining response{pendingInputCount === 1 ? "" : "s"} before export unlocks.
        </p>
      ) : null}
    </div>
  )
}
