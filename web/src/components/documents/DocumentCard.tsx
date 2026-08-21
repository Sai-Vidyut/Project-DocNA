import { useRef, useState } from "react"
import { ArrowRight, FileText, MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DocumentMenu } from "./DocumentMenu"
import { WorkspaceStatusDot } from "./WorkspaceStatusDot"
import type { WorkspaceSummary } from "@/lib/types"
import { workspaceMetaLine, workspaceStatusLabel } from "@/lib/workspace-utils"
import { cn } from "@/lib/utils"

interface DocumentRowProps {
  workspace: WorkspaceSummary
  peers: WorkspaceSummary[]
  muted?: boolean
  onOpen: (workspaceId: string) => void
  onRename: (workspaceId: string, displayName: string) => Promise<void>
  onDelete: (workspaceId: string) => Promise<void>
}

export function DocumentRow({ workspace, peers, muted, onOpen, onRename, onDelete }: DocumentRowProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [nameDraft, setNameDraft] = useState(workspace.display_name)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)

  const submitRename = async () => {
    const trimmed = nameDraft.trim()
    if (!trimmed || trimmed === workspace.display_name) {
      setRenaming(false)
      setNameDraft(workspace.display_name)
      return
    }
    setBusy(true)
    try {
      await onRename(workspace.workspace_id, trimmed)
      setRenaming(false)
    } finally {
      setBusy(false)
    }
  }

  const confirmRemoval = async () => {
    setBusy(true)
    try {
      await onDelete(workspace.workspace_id)
    } finally {
      setBusy(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div className={cn("doc-row glass-1 group relative rounded-md", muted && "opacity-75")}>
      <button
        type="button"
        className="flex w-full items-center gap-3 px-3.5 py-3 pr-12 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.35)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))] rounded-md"
        onClick={() => onOpen(workspace.workspace_id)}
      >
        <div
          className="flex size-9 shrink-0 items-center justify-center rounded-md border border-[hsla(var(--foreground)/0.05)] bg-[hsla(var(--background)/0.4)] text-[hsl(var(--primary))]"
          aria-hidden
        >
          <FileText className="size-4" strokeWidth={1.5} />
        </div>

        <div className="min-w-0 flex-1">
          {renaming ? (
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                e.stopPropagation()
                void submitRename()
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <input
                className="min-w-0 flex-1 rounded border border-[hsla(var(--foreground)/0.1)] bg-[hsla(var(--background)/0.5)] px-2 py-1 text-sm outline-none focus:border-[hsla(var(--primary)/0.35)]"
                value={nameDraft}
                autoFocus
                onChange={(e) => setNameDraft(e.target.value)}
              />
              <Button type="submit" variant="secondary" disabled={busy} onClick={(e) => e.stopPropagation()}>
                Save
              </Button>
            </form>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3">
                <p className="m-0 truncate text-[0.875rem] font-medium text-[hsl(var(--foreground))]">
                  {workspace.display_name}
                </p>
                <WorkspaceStatusDot
                  status={workspace.status}
                  label={workspaceStatusLabel(workspace.status)}
                  muted={muted}
                  className="hidden sm:inline-flex"
                />
              </div>
              <p className="mt-0.5 mb-0 type-meta">{workspaceMetaLine(workspace, peers)}</p>
            </>
          )}
        </div>

        <ArrowRight
          className="size-4 shrink-0 text-[hsla(var(--foreground)/0.2)] transition-[transform,color,opacity] duration-200 group-hover:translate-x-0.5 group-hover:text-[hsl(var(--primary))] group-hover:opacity-100 opacity-60"
          aria-hidden
        />
      </button>

      <div className="absolute right-2 top-1/2 -translate-y-1/2">
        <button
          ref={menuButtonRef}
          type="button"
          className="inline-flex size-8 items-center justify-center rounded-md border border-transparent text-[hsl(var(--muted))] opacity-0 transition-opacity hover:bg-[hsla(var(--foreground)/0.05)] hover:text-[hsl(var(--foreground))] group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.35)] data-[open=true]:opacity-100"
          aria-label="Document actions"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          data-open={menuOpen}
          onClick={(e) => {
            e.stopPropagation()
            setMenuOpen((open) => !open)
          }}
        >
          <MoreHorizontal className="size-4" aria-hidden />
        </button>
      </div>

      <DocumentMenu
        open={menuOpen}
        anchorRef={menuButtonRef}
        onClose={() => setMenuOpen(false)}
        onRename={() => setRenaming(true)}
        onDelete={() => setConfirmDelete(true)}
      />

      {confirmDelete ? (
        <div className="border-t border-[hsla(var(--foreground)/0.05)] px-3.5 py-2.5" onClick={(e) => e.stopPropagation()}>
          <p className="m-0 text-[0.8125rem] text-[hsl(var(--foreground))]">
            Delete “{workspace.display_name}”? This cannot be undone.
          </p>
          <div className="mt-2 flex gap-2">
            <Button variant="secondary" disabled={busy} onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button
              variant="ghost"
              className="text-[hsl(var(--error))]"
              disabled={busy}
              onClick={() => void confirmRemoval()}
            >
              Delete
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

/** @deprecated use DocumentRow */
export const DocumentCard = DocumentRow
