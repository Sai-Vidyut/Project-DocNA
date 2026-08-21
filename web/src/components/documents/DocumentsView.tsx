import { Button } from "@/components/ui/button"
import { DocumentRow } from "./DocumentCard"
import { WorkspaceHero } from "./WorkspaceHero"
import type { WorkspaceSummary } from "@/lib/types"

interface DocumentsViewProps {
  workspaces: WorkspaceSummary[]
  loading: boolean
  loadFailed: boolean
  error: string
  onRefresh: () => void
  onNewDocument: () => void
  onDropFile?: (file: File) => void
  onOpen: (workspaceId: string) => void
  onRename: (workspaceId: string, displayName: string) => Promise<void>
  onDelete: (workspaceId: string) => Promise<void>
}

function DocumentsLoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="py-12 text-center" role="alert">
      <p className="m-0 text-sm font-medium text-[hsl(var(--foreground))]">
        {message || "Couldn't load your documents."}
      </p>
      <p className="mt-1.5 mb-0 type-meta">Check that DocNA is running, then try again.</p>
      <Button type="button" variant="secondary" className="mt-4" onClick={onRetry}>
        Retry
      </Button>
    </div>
  )
}

function DocumentsEmptyState({ onNewDocument, onDropFile }: { onNewDocument: () => void; onDropFile?: (file: File) => void }) {
  return (
    <div className="relative py-6 text-center">
      <div
        className="pointer-events-none absolute left-1/2 top-8 size-48 -translate-x-1/2 rounded-full bg-[radial-gradient(circle,hsla(var(--primary)/0.08),transparent_70%)] blur-2xl"
        aria-hidden
      />
      <span className="relative mb-4 inline-flex text-lg text-[hsla(var(--primary)/0.65)]" aria-hidden>
        ◇
      </span>
      <p className="relative m-0 type-workspace-title text-[hsl(var(--foreground))]">
        Your workspace is empty
      </p>
      <p className="relative mt-2 mb-0 max-w-[18rem] mx-auto text-sm leading-relaxed text-[hsl(var(--muted))]">
        Upload a DOCX and DocNA will help you complete it.
      </p>
      <div className="relative mt-8">
        <WorkspaceHero onNewDocument={onNewDocument} onDropFile={onDropFile} />
      </div>
    </div>
  )
}

export function DocumentsView({
  workspaces,
  loading,
  loadFailed,
  error,
  onRefresh,
  onNewDocument,
  onDropFile,
  onOpen,
  onRename,
  onDelete,
}: DocumentsViewProps) {
  const primary = workspaces.filter((item) => item.status !== "failed")
  const failed = workspaces.filter((item) => item.status === "failed")
  const showEmpty = !loading && !loadFailed && workspaces.length === 0
  const showList = !loading && !loadFailed && workspaces.length > 0

  return (
    <section
      className="documents-home mx-auto w-full px-4 py-6 md:px-6 md:py-8"
      aria-labelledby="documents-heading"
    >
      <header className="mb-6 md:mb-8">
        <h1 id="documents-heading" className="m-0 type-workspace-title text-[hsl(var(--foreground))]">
          Your workspace
        </h1>
        <p className="mt-1.5 mb-0 text-sm text-[hsl(var(--muted))]">
          {showEmpty
            ? "Documents, drafts, and completed work live here."
            : "Documents you've worked on."}
        </p>
      </header>

      {loading ? (
        <p className="m-0 py-16 text-center text-sm text-[hsl(var(--muted))]" aria-live="polite">
          Loading documents…
        </p>
      ) : null}

      {!loading && loadFailed ? <DocumentsLoadError message={error} onRetry={onRefresh} /> : null}

      {showEmpty ? (
        <DocumentsEmptyState onNewDocument={onNewDocument} onDropFile={onDropFile} />
      ) : null}

      {showList ? (
        <div className="space-y-8">
          <WorkspaceHero compact onNewDocument={onNewDocument} onDropFile={onDropFile} />

          {primary.length > 0 ? (
            <div>
              <div className="workspace-divider mb-4" aria-hidden />
              <p className="type-section-label mb-3">Recent</p>
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {primary.map((workspace) => (
                  <li key={workspace.workspace_id}>
                    <DocumentRow
                      workspace={workspace}
                      peers={workspaces}
                      onOpen={onOpen}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {failed.length > 0 ? (
            <div>
              <p className="type-section-label mb-2 text-[hsl(var(--muted-foreground))]">Could not process</p>
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {failed.map((workspace) => (
                  <li key={workspace.workspace_id}>
                    <DocumentRow
                      workspace={workspace}
                      peers={workspaces}
                      muted
                      onOpen={onOpen}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
