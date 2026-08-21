import type { WorkspaceStatus, WorkspaceSummary } from "@/lib/types"

export function workspaceStatusLabel(status: WorkspaceStatus): string {
  switch (status) {
    case "processing":
      return "Processing"
    case "needs_input":
      return "In progress"
    case "needs_review":
      return "Needs review"
    case "ready":
      return "Ready"
    case "failed":
      return "Failed"
    default:
      return status
  }
}

export function workspaceActionLabel(status: WorkspaceStatus): string {
  switch (status) {
    case "processing":
      return "Open"
    case "needs_input":
      return "Continue"
    case "needs_review":
      return "Review"
    case "ready":
      return "Open"
    case "failed":
      return "View"
    default:
      return "Open"
  }
}

export function workspaceDetailLine(workspace: WorkspaceSummary): string {
  switch (workspace.status) {
    case "processing":
      return "DocNA is working on your document."
    case "needs_input":
      return `${workspace.items_remaining} response${workspace.items_remaining === 1 ? "" : "s"} remaining`
    case "needs_review":
      return `${workspace.items_needing_review} item${workspace.items_needing_review === 1 ? "" : "s"} need attention`
    case "ready":
      return workspace.download_ready ? "Ready to export" : "All questions completed"
    case "failed":
      return workspace.error_message || "Unable to process document"
    default:
      return ""
  }
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return "Edited just now"
  if (minutes < 60) return `Edited ${minutes} minute${minutes === 1 ? "" : "s"} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    if (hours < 2) return "Edited today"
    return `Edited ${hours} hour${hours === 1 ? "" : "s"} ago`
  }
  const days = Math.floor(hours / 24)
  if (days === 1) return "Edited yesterday"
  return `Edited ${days} days ago`
}

export function workspaceMetaLine(workspace: WorkspaceSummary, peers: WorkspaceSummary[]): string {
  const parts: string[] = [formatRelativeTime(workspace.updated_at)]

  const duplicateNames = peers.filter((item) => item.display_name === workspace.display_name).length > 1
  if (duplicateNames || workspace.document_name.replace(/\.docx$/i, "") !== workspace.display_name) {
    parts.push(workspace.document_name)
  }

  if (workspace.questions_detected > 0) {
    parts.push(`${workspace.questions_detected} question${workspace.questions_detected === 1 ? "" : "s"}`)
  }
  if (workspace.answers_generated > 0) {
    parts.push(`${workspace.answers_generated} answered`)
  }

  return parts.join(" · ")
}
