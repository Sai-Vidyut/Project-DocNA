import { CheckCircle2 } from "lucide-react"

export function QuestionsComplete() {
  return (
    <div className="flex items-start gap-2 py-2">
      <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-[hsl(var(--success))]" aria-hidden />
      <div>
        <p className="m-0 text-[0.8125rem] font-medium text-[hsl(var(--foreground))]">
          All questions requiring your input are complete
        </p>
        <p className="mt-0.5 mb-0 type-meta">Review the document, then export when ready.</p>
      </div>
    </div>
  )
}
