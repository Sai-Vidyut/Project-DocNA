import type { ReviewReport } from "@/lib/types"

interface ReviewSummaryProps {
  report: ReviewReport
  attentionCount: number
  compact?: boolean
}

export function ReviewSummary({ report, attentionCount }: ReviewSummaryProps) {
  const summary = report.summary

  return (
    <dl className="m-0 grid grid-cols-3 gap-1.5 text-center">
      <div className="rounded-md border border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--background)/0.3)] px-1.5 py-1.5">
        <dt className="text-[0.6rem] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Questions</dt>
        <dd className="m-0 text-sm font-medium tabular-nums text-[hsl(var(--foreground))]">
          {summary.questions_detected ?? 0}
        </dd>
      </div>
      <div className="rounded-md border border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--background)/0.3)] px-1.5 py-1.5">
        <dt className="text-[0.6rem] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Answered</dt>
        <dd className="m-0 text-sm font-medium tabular-nums text-[hsl(var(--foreground))]">
          {summary.answers_generated ?? 0}
        </dd>
      </div>
      <div className="rounded-md border border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--background)/0.3)] px-1.5 py-1.5">
        <dt className="text-[0.6rem] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Need input</dt>
        <dd className="m-0 text-sm font-medium tabular-nums text-[hsl(var(--foreground))]">{attentionCount}</dd>
      </div>
    </dl>
  )
}
