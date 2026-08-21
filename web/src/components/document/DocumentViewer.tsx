import type { DocumentPreview } from "@/lib/types"
import { AnswerRegion } from "./AnswerRegion"
import { cn } from "@/lib/utils"

interface DocumentViewerProps {
  preview: DocumentPreview | null
  answerState: Map<string, string>
  originalAnswers: Map<string, string>
  onAnswerChange: (taskId: string, text: string) => void
}

export function DocumentViewer({ preview, answerState, originalAnswers, onAnswerChange }: DocumentViewerProps) {
  if (!preview?.blocks?.length) {
    return <p className="preview-loading m-0 font-sans text-sm text-[hsl(var(--muted))]">Preview unavailable.</p>
  }

  return (
    <div className="document-preview" id="document-preview">
      {preview.blocks.map((block) => (
        <p
          key={block.block_id}
          className={cn(
            "preview-block mb-3 whitespace-pre-wrap break-words",
            block.kind === "heading" && "preview-block-heading",
            block.kind === "list_item" && "preview-block-list",
          )}
        >
          {block.parts.map((part, index) => {
            if (part.type === "text") {
              return <span key={index}>{part.value}</span>
            }
            const taskId = part.task_id || ""
            const text = answerState.get(taskId) ?? part.value
            const original = (originalAnswers.get(taskId) || "").trim()
            const edited = text.trim() !== original
            return (
              <AnswerRegion
                key={`${taskId}-${index}`}
                taskId={taskId}
                value={text}
                editable={Boolean(part.editable)}
                edited={edited}
                onChange={(next) => onAnswerChange(taskId, next)}
              />
            )
          })}
        </p>
      ))}
    </div>
  )
}
