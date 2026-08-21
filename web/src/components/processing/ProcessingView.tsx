import type { JobStatus } from "@/lib/types"
import { ProcessingOrb } from "./ProcessingOrb"
import { ProcessingSteps, currentProcessingLabel } from "./ProcessingSteps"

interface ProcessingViewProps {
  filename: string
  status: JobStatus
  questionCount?: number
}

export function ProcessingView({ filename, status, questionCount }: ProcessingViewProps) {
  const activeLabel = currentProcessingLabel(status)

  return (
    <section
      className="flex min-h-[calc(100vh-var(--header-height))] flex-col items-center justify-center px-4 py-8"
      aria-live="polite"
      aria-busy={status !== "completed" && status !== "failed"}
    >
      <div className="w-full max-w-[22rem] text-center">
        <p className="m-0 truncate text-[0.9375rem] font-medium text-[hsl(var(--foreground))]">{filename}</p>

        <p className="mt-5 mb-0 type-section-label text-[hsl(var(--muted-foreground))]">
          Preparing your document
        </p>

        <ProcessingOrb activeLabel={activeLabel} />

        <p className="m-0 text-[0.9375rem] font-medium text-[hsl(var(--foreground))]" role="status">
          {activeLabel}
        </p>
        {questionCount != null && questionCount > 0 ? (
          <p className="mt-1 mb-0 type-meta">
            {questionCount} question{questionCount === 1 ? "" : "s"} found
          </p>
        ) : null}

        <div className="mt-7 border-t border-[hsla(var(--foreground)/0.05)] pt-5">
          <ProcessingSteps status={status} />
        </div>

        <p className="mt-5 mb-0 type-meta">Longer documents may take a minute.</p>
      </div>
    </section>
  )
}
