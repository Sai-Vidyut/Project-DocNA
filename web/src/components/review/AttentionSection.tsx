import type { ReviewTaskEntry } from "@/lib/types"
import type { AutosaveStatus } from "@/lib/use-autosave"
import { AnswerCard } from "./AnswerCard"

interface AttentionSectionProps {
  items: ReviewTaskEntry[]
  answerState: Map<string, string>
  originalAnswers: Map<string, string>
  autosaveStatus: AutosaveStatus
  onAnswerChange: (taskId: string, text: string) => void
  onAskAI: (item: ReviewTaskEntry, anchor: HTMLElement) => void
}

export function AttentionSection({
  items,
  answerState,
  originalAnswers,
  autosaveStatus,
  onAnswerChange,
  onAskAI,
}: AttentionSectionProps) {
  return (
    <section aria-labelledby="cards-heading">
      <h3 id="cards-heading" className="type-section-label mb-2">
        Needs your input
      </h3>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <AnswerCard
            key={item.task_id}
            item={item}
            value={answerState.get(item.task_id) ?? item.answer_text ?? ""}
            originalValue={originalAnswers.get(item.task_id) ?? item.answer_text ?? ""}
            autosaveStatus={autosaveStatus}
            onChange={(text) => onAnswerChange(item.task_id, text)}
            onAskAI={(anchor) => onAskAI(item, anchor)}
          />
        ))}
      </div>
    </section>
  )
}
