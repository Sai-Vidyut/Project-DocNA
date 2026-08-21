import type { ReviewReport, ReviewTaskEntry } from "./types"

export function isUserInputPlaceholder(text: string | null | undefined): boolean {
  const normalized = (text || "").trim()
  if (!normalized) return true
  const lowered = normalized.toLowerCase().replace(/\.$/, "")
  if (lowered === "[your response]" || lowered.startsWith("[your response")) return true
  if (lowered === "user input required" || lowered === "user input is required") return true
  return false
}

function needsQuestionCard(entry: ReviewTaskEntry): boolean {
  if (entry.requires_user_input) return true
  // Defensive: malformed review rows that show placeholders in preview but omit the flag.
  if (entry.editable && isUserInputPlaceholder(entry.answer_text)) return true
  return false
}

export function effectiveCardStatus(item: ReviewTaskEntry): string | null {
  if (item.requires_user_input && !item.editable) return "needs_review"
  return item.card_status ?? null
}

export function collectQuestionCardItems(report: ReviewReport): ReviewTaskEntry[] {
  const items: ReviewTaskEntry[] = []
  const seen = new Set<string>()
  for (const source of [...report.answered, ...report.skipped, ...report.flagged]) {
    if (seen.has(source.task_id)) continue
    if (!needsQuestionCard(source)) continue
    seen.add(source.task_id)
    const cardStatus = effectiveCardStatus(source)
    items.push(cardStatus && cardStatus !== source.card_status ? { ...source, card_status: cardStatus } : source)
  }
  return items
}

export function buildInitialAnswerState(report: ReviewReport): {
  answers: Map<string, string>
  originals: Map<string, string>
} {
  const answers = new Map<string, string>()
  const originals = new Map<string, string>()
  const cardTaskIds = new Set(collectQuestionCardItems(report).map((item) => item.task_id))
  for (const item of report.answered) {
    if (!item.editable && !cardTaskIds.has(item.task_id)) continue
    const text = item.answer_text || ""
    answers.set(item.task_id, text)
    originals.set(item.task_id, text)
  }
  return { answers, originals }
}

export function collectEdits(
  answerState: Map<string, string>,
  originalAnswers: Map<string, string>,
): { task_id: string; text: string }[] {
  const edits: { task_id: string; text: string }[] = []
  for (const [taskId, text] of answerState.entries()) {
    const trimmed = text.trim()
    if (!trimmed) throw new Error("Answers cannot be empty.")
    const original = (originalAnswers.get(taskId) || "").trim()
    if (trimmed !== original) edits.push({ task_id: taskId, text: trimmed })
  }
  return edits
}
