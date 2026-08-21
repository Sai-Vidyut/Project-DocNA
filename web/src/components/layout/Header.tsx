import { CosmicGlowButton } from "@/components/ui/spark-button"
import { Button } from "@/components/ui/button"
import type { AppView } from "@/lib/types"
import { cn } from "@/lib/utils"

interface HeaderProps {
  view: AppView
  filename?: string
  status?: string
  onNewDocument: () => void
  onDocuments?: () => void
  hideNewDocument?: boolean
}

export function Header({
  view,
  filename,
  status,
  onNewDocument,
  onDocuments,
  hideNewDocument,
}: HeaderProps) {
  const isDocuments = view === "documents"
  const isUpload = view === "upload"
  const showDocumentContext = !isUpload && !isDocuments && Boolean(filename || status)

  return (
    <header
      className="sticky top-0 z-30 border-b border-[hsla(var(--foreground)/0.05)] bg-[hsla(var(--background)/0.72)] backdrop-blur-xl supports-[backdrop-filter]:bg-[hsla(var(--background)/0.55)]"
      style={{ height: "var(--header-height)" }}
    >
      <div className="mx-auto flex h-full max-w-[1180px] items-center gap-3 px-4 md:px-6">
        <div className="flex min-w-0 shrink-0 items-center gap-2">
          <span className="text-[0.65rem] text-[hsla(var(--primary)/0.8)]" aria-hidden>
            ◇
          </span>
          <span className="text-[0.8125rem] font-semibold tracking-tight">DocNA</span>
          {(isDocuments || isUpload) && (
            <>
              <span className="text-[hsla(var(--foreground)/0.18)]" aria-hidden>
                /
              </span>
              <span className="text-[0.8125rem] text-[hsl(var(--muted))]">Documents</span>
            </>
          )}
        </div>

        {showDocumentContext ? (
          <div className="flex min-w-0 flex-1 items-center justify-center gap-2 px-2 text-[0.8125rem]" aria-live="polite">
            {onDocuments ? (
              <>
                <button
                  type="button"
                  className="hidden shrink-0 text-[hsl(var(--muted))] hover:text-[hsl(var(--foreground))] sm:inline"
                  onClick={onDocuments}
                >
                  Documents
                </button>
                <span className="hidden text-[hsla(var(--foreground)/0.2)] sm:inline" aria-hidden>
                  /
                </span>
              </>
            ) : null}
            {filename ? (
              <span className="max-w-[min(360px,46vw)] truncate font-medium text-[hsl(var(--foreground))]">
                {filename}
              </span>
            ) : null}
            {status ? (
              <span
                className={cn(
                  "shrink-0 text-[0.75rem]",
                  status === "Processing" ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--muted))]",
                )}
              >
                {status}
              </span>
            ) : null}
          </div>
        ) : (
          <div className="flex-1" />
        )}

        <div className="flex shrink-0 items-center gap-1">
          {!isDocuments && !isUpload && onDocuments ? (
            <Button variant="ghost" className="h-7 px-2 text-[0.75rem]" onClick={onDocuments}>
              Documents
            </Button>
          ) : null}
          {isDocuments && !hideNewDocument ? (
            <CosmicGlowButton type="button" compact onClick={onNewDocument}>
              New document
            </CosmicGlowButton>
          ) : null}
          {!hideNewDocument && !isDocuments && !isUpload ? (
            <Button variant="ghost" className="h-7 px-2 text-[0.75rem]" onClick={onNewDocument}>
              New document
            </Button>
          ) : null}
          {isUpload ? (
            <Button variant="ghost" className="h-7 px-2 text-[0.75rem]" onClick={onDocuments ?? onNewDocument}>
              Documents
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  )
}
