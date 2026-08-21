import { useRef, useState, type DragEvent, type KeyboardEvent } from "react"
import { FileUp } from "lucide-react"
import { CosmicGlowButton } from "@/components/ui/spark-button"
import { cn } from "@/lib/utils"
import { isDocxFile } from "@/lib/format"

interface WorkspaceHeroProps {
  compact?: boolean
  onNewDocument: () => void
  onDropFile?: (file: File) => void
}

export function WorkspaceHero({ compact, onNewDocument, onDropFile }: WorkspaceHeroProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const accept = (file: File | undefined) => {
    if (!file || !isDocxFile(file)) return
    if (onDropFile) onDropFile(file)
    else onNewDocument()
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    accept(event.dataTransfer.files?.[0])
  }

  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      inputRef.current?.click()
    }
  }

  return (
    <div
      className={cn(
        "workspace-hero relative overflow-hidden rounded-lg",
        compact ? "glass-1 px-4 py-4" : "glass-2 px-6 py-10 md:py-12",
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,hsla(var(--primary)/0.08),transparent_58%)]"
        aria-hidden
      />

      <div
        role="button"
        tabIndex={0}
        aria-label="Drop a DOCX file or start a new document"
        className={cn(
          "relative flex flex-col items-center text-center outline-none transition-colors",
          "focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.35)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))] rounded-md",
          dragOver && "text-[hsl(var(--primary))]",
        )}
        onClick={() => inputRef.current?.click()}
        onKeyDown={onKey}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <div
          className={cn(
            "mb-3 flex items-center justify-center rounded-md border border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--background)/0.35)] text-[hsl(var(--primary))]",
            compact ? "size-9" : "size-11",
          )}
          aria-hidden
        >
          <FileUp className={compact ? "size-4" : "size-5"} strokeWidth={1.5} />
        </div>

        {!compact ? (
          <>
            <p className="type-section-label mb-2">Drop / open document</p>
            <p className="m-0 text-[0.9375rem] font-medium text-[hsl(var(--foreground))]">Start with a DOCX</p>
            <p className="mt-1.5 mb-0 max-w-[22rem] text-sm leading-relaxed text-[hsl(var(--muted))]">
              DocNA will analyze your document, draft answers, and help you complete the rest.
            </p>
          </>
        ) : (
          <p className="m-0 text-sm text-[hsl(var(--muted))]">
            Drop a DOCX here or{" "}
            <span className="text-[hsl(var(--foreground))]">choose a file</span>
          </p>
        )}

        <CosmicGlowButton
          type="button"
          compact={compact}
          className={cn(compact ? "mt-3" : "mt-5")}
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation()
            onNewDocument()
          }}
        >
          New document
        </CosmicGlowButton>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        hidden
        onChange={(e) => {
          accept(e.target.files?.[0])
          e.target.value = ""
        }}
      />
    </div>
  )
}
