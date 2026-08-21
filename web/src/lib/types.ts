export type AppView = "documents" | "upload" | "processing" | "review" | "error"

export type WorkspaceStatus = "processing" | "needs_input" | "ready" | "needs_review" | "failed"

export type JobStatus =
  | "queued"
  | "processing"
  | "parsing"
  | "detecting"
  | "answering"
  | "placing"
  | "validating"
  | "completed"
  | "failed"

export interface JobCreateResponse {
  job_id: string
  workspace_id?: string
  status: JobStatus
}

export interface WorkspaceSummary {
  workspace_id: string
  job_id: string
  document_name: string
  display_name: string
  created_at: string
  updated_at: string
  status: WorkspaceStatus
  questions_detected: number
  answers_generated: number
  items_remaining: number
  items_needing_review: number
  edited_task_ids: string[]
  export_filename: string
  download_ready: boolean
  error_message?: string | null
}

export interface WorkspacesListResponse {
  workspaces: WorkspaceSummary[]
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  original_filename?: string
  error_message?: string | null
}

export interface ReviewSummary {
  questions_detected: number
  answers_generated: number
  items_skipped: number
  items_needing_review: number
}

export interface ReviewTaskEntry {
  task_id: string
  task_text: string
  task_kind: string
  answer_status: string
  answer_text?: string | null
  answer_confidence?: number | null
  placement_strategy?: string | null
  placement_label?: string
  review_flags?: string[]
  skip_reason?: string | null
  attention_reason?: string | null
  needs_review?: boolean
  editable?: boolean
  edited?: boolean
  answer_source?: "ai" | "user"
  requires_user_input?: boolean
  card_status?: string | null
}

export interface ReviewReport {
  job_id: string
  status: JobStatus
  summary: ReviewSummary
  answered: ReviewTaskEntry[]
  skipped: ReviewTaskEntry[]
  flagged: ReviewTaskEntry[]
  warnings?: string[]
  download_ready: boolean
}

export interface PreviewPart {
  type: "text" | "answer"
  value: string
  task_id?: string | null
  editable?: boolean
}

export interface PreviewBlock {
  block_id: string
  kind: string
  parts: PreviewPart[]
}

export interface DocumentPreview {
  job_id: string
  filename: string
  blocks: PreviewBlock[]
}

export interface ReviewEdit {
  task_id: string
  text: string
}

export interface AssistMessage {
  role: "user" | "assistant"
  content: string
}

export interface AssistResponse {
  message: string
  example_response?: string | null
}
