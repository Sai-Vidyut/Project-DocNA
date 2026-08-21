import { Button } from "@/components/ui/button"
import { CosmicGlowButton } from "@/components/ui/spark-button"
import { DropZone } from "./DropZone"
import { formatFileSize } from "@/lib/format"

interface UploadViewProps {
  selectedFile: File | null
  error: string
  analyzing: boolean
  onSelectFile: (file: File | null) => void
  onAnalyze: () => void
  onBack?: () => void
  dropzoneRef?: React.RefObject<HTMLDivElement | null>
}

export function UploadView({
  selectedFile,
  error,
  analyzing,
  onSelectFile,
  onAnalyze,
  onBack,
}: UploadViewProps) {
  return (
    <section
      className="flex min-h-[calc(100vh-var(--header-height))] items-center justify-center px-4 py-10"
      aria-labelledby="upload-heading"
    >
      <div className="w-full max-w-[440px]">
        {onBack ? (
          <div className="mb-6">
            <Button variant="ghost" className="h-7 px-2 text-[0.75rem]" onClick={onBack}>
              ← Documents
            </Button>
          </div>
        ) : null}

        <div className="mb-6 text-center">
          <h1 id="upload-heading" className="m-0 type-workspace-title text-[hsl(var(--foreground))]">
            New document
          </h1>
          <p className="mt-2 mb-0 text-sm leading-relaxed text-[hsl(var(--muted))]">
            Upload a DOCX worksheet or form. DocNA finds questions, drafts answers, and helps you finish the rest.
          </p>
        </div>

        <DropZone onSelectFile={(file) => onSelectFile(file)} />

        {selectedFile ? (
          <div
            className="mt-3 flex items-center justify-center gap-2 text-sm"
            aria-live="polite"
          >
            <span className="text-[hsl(var(--foreground))]">{selectedFile.name}</span>
            <span className="type-meta">{formatFileSize(selectedFile.size)}</span>
          </div>
        ) : null}

        {error ? (
          <p className="mt-2 text-center text-sm text-[hsl(var(--error))]" role="alert">
            {error}
          </p>
        ) : null}

        <div className="mt-5 flex justify-center">
          <CosmicGlowButton disabled={!selectedFile || analyzing} onClick={onAnalyze}>
            {analyzing ? "Uploading…" : "Analyze document"}
          </CosmicGlowButton>
        </div>
      </div>
    </section>
  )
}
