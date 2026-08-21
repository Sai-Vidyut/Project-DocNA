import type { JobStatus } from "./types"

export const TERMINAL_STATUSES = new Set<JobStatus>(["completed", "failed"])

export const STAGE_ORDER = [
  { key: "queued", label: "Upload", stepLabel: "Upload" },
  { key: "parsing", label: "Read document", stepLabel: "Read document" },
  { key: "detecting", label: "Find questions", stepLabel: "Find questions" },
  { key: "answering", label: "Generate answers", stepLabel: "Generate answers" },
  { key: "placing", label: "Write answers", stepLabel: "Write answers" },
  { key: "validating", label: "Prepare review", stepLabel: "Prepare review" },
] as const

/** Friendly label for the currently active processing stage. */
export const CURRENT_STATUS_LABEL: Record<string, string> = {
  queued: "Waiting to start",
  processing: "Reading document",
  parsing: "Reading document",
  detecting: "Finding questions",
  answering: "Generating answers",
  placing: "Writing answers",
  validating: "Checking document",
  completed: "Preparing review",
  failed: "Processing failed",
}

export const STATUS_TO_STAGE: Record<string, string> = {
  queued: "queued",
  processing: "queued",
  parsing: "parsing",
  detecting: "detecting",
  answering: "answering",
  placing: "placing",
  validating: "validating",
  completed: "validating",
}

export const CARD_STATUS_LABELS: Record<string, string> = {
  personal_response: "Personal response",
  needs_your_input: "Needs your input",
  needs_input: "Needs your input",
  needs_review: "Needs review",
  placement_review: "Needs review",
}
