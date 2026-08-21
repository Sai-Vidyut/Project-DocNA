import { useRef } from "react"
import { CosmicGlowButton } from "@/components/ui/spark-button"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { GlassSurface } from "@/components/ui/glass-surface"
import { CARD_STATUS_LABELS } from "@/lib/constants"
import { taskLabel } from "@/lib/format"
import type { AutosaveStatus } from "@/lib/use-autosave"
import type { ReviewTaskEntry } from "@/lib/types"

interface AnswerCardProps {
  item: ReviewTaskEntry
  value: string
  originalValue: string
  autosaveStatus?: AutosaveStatus
  onChange: (text: string) => void
  onAskAI: (anchor: HTMLElement) => void
}

function cardStatusBadges(
  item: ReviewTaskEntry,
  value: string,
  originalValue: string,
  autosaveStatus?: AutosaveStatus,
): { label: string; variant: "warning" | "success" | "default" }[] {
  const badges: { label: string; variant: "warning" | "success" | "default" }[] = []
  const statusLabel = CARD_STATUS_LABELS[item.card_status || ""] || "Needs input"
  badges.push({ label: statusLabel, variant: "warning" })

  const trimmed = value.trim()
  const isEdited = trimmed !== originalValue.trim() && trimmed.length > 0
  if (isEdited) {
    if (autosaveStatus === "saving") badges.push({ label: "Saving", variant: "default" })
    else if (autosaveStatus === "error") badges.push({ label: "Unsaved", variant: "warning" })
    else if (autosaveStatus === "saved") badges.push({ label: "Saved", variant: "success" })
    else badges.push({ label: "Edited", variant: "default" })
  }

  if (item.needs_review) {
    badges.push({ label: "Needs review", variant: "warning" })
  }

  return badges
}

export function AnswerCard({
  item,
  value,
  originalValue,
  autosaveStatus,
  onChange,
  onAskAI,
}: AnswerCardProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const badges = cardStatusBadges(item, value, originalValue, autosaveStatus)

  return (
    <article>
      <GlassSurface
        level={1}
        interactive
        className="overflow-hidden focus-within:border-[hsla(var(--primary)/0.18)]"
      >
        <div className="px-3 pt-2.5 pb-2">
          <p className="card-question m-0 text-[0.8125rem] leading-snug text-[hsl(var(--foreground))]">
            {item.task_text}
          </p>
          {item.attention_reason ? (
            <p className="mt-1 mb-0 text-[0.72rem] leading-snug text-[hsl(var(--muted))]">{item.attention_reason}</p>
          ) : null}
          <div className="mt-1.5 flex flex-wrap gap-1">
            {badges.map((badge) => (
              <Badge key={badge.label} variant={badge.variant}>
                {badge.label}
              </Badge>
            ))}
          </div>
        </div>
        <div className="border-t border-[hsla(var(--foreground)/0.04)] px-3 py-2">
          <Textarea
            ref={inputRef}
            className="card-answer-input min-h-10 text-[0.8125rem]"
            data-card-input={item.task_id}
            value={value}
            placeholder="Write your answer…"
            aria-label={`Answer for ${taskLabel(item.task_text)}`}
            onChange={(e) => onChange(e.target.value)}
          />
          <div className="mt-1.5 flex gap-1.5">
            <CosmicGlowButton compact type="button" onClick={(e) => onAskAI(e.currentTarget)}>
              Ask AI
            </CosmicGlowButton>
            <Button
              variant="secondary"
              type="button"
              className="text-xs"
              onClick={() => inputRef.current?.focus()}
            >
              Answer
            </Button>
          </div>
        </div>
      </GlassSurface>
    </article>
  )
}
