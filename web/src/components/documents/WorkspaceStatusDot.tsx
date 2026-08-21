import type { WorkspaceStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

const STATUS_DOT: Record<WorkspaceStatus, string> = {
  processing: "bg-[hsl(var(--primary))] shadow-[0_0_6px_hsla(var(--primary)/0.55)]",
  needs_input: "bg-[hsl(var(--warning))] shadow-[0_0_6px_hsla(var(--warning)/0.45)]",
  needs_review: "bg-[hsl(258_72%_62%)] shadow-[0_0_6px_hsla(258_72%_62%/0.4)]",
  ready: "bg-[hsl(var(--success))] shadow-[0_0_6px_hsla(var(--success)/0.45)]",
  failed: "bg-[hsl(var(--error))] shadow-[0_0_6px_hsla(var(--error)/0.4)]",
}

interface WorkspaceStatusDotProps {
  status: WorkspaceStatus
  label: string
  muted?: boolean
  className?: string
}

export function WorkspaceStatusDot({ status, label, muted, className }: WorkspaceStatusDotProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 text-[0.6875rem]",
        muted ? "text-[hsl(var(--muted-foreground))]" : "text-[hsl(var(--muted))]",
        className,
      )}
    >
      <span className={cn("status-dot", STATUS_DOT[status])} aria-hidden />
      <span>{label}</span>
    </span>
  )
}
