import type {
  AssistMessage,
  AssistResponse,
  DocumentPreview,
  JobCreateResponse,
  JobStatusResponse,
  ReviewEdit,
  ReviewReport,
  WorkspaceSummary,
  WorkspacesListResponse,
} from "./types"

async function parseJson<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T
  } catch {
    return null
  }
}

export function uploadErrorMessage(status: number, payload: { detail?: string } | null): string {
  if (status === 400) {
    const detail = payload?.detail || ""
    if (detail.includes("Unsupported file type")) return "DocNA supports DOCX files only."
    if (detail.includes("valid DOCX")) return "Please make sure the file is a valid DOCX."
    if (detail.includes("maximum size")) return "This file exceeds the maximum upload size."
    if (detail.includes("empty")) return "The selected file is empty."
    return detail || "Could not upload this file."
  }
  if (status >= 500) return "DocNA could not start processing. Please try again."
  return "Could not upload this file. Check your connection and try again."
}

export async function uploadDocument(file: File): Promise<JobCreateResponse> {
  const formData = new FormData()
  formData.append("file", file, file.name)
  let response: Response
  try {
    response = await fetch("/jobs", { method: "POST", body: formData })
  } catch {
    throw new Error("Could not reach DocNA. Check your connection and try again.")
  }
  const payload = await parseJson<{ detail?: string } & JobCreateResponse>(response)
  if (!response.ok) throw new Error(uploadErrorMessage(response.status, payload))
  return payload as JobCreateResponse
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`/jobs/${jobId}`)
  const payload = await parseJson<{ detail?: string } & JobStatusResponse>(response)
  if (!response.ok) throw new Error(payload?.detail || "Could not load job status.")
  return payload as JobStatusResponse
}

export async function fetchReview(jobId: string): Promise<ReviewReport> {
  const response = await fetch(`/jobs/${jobId}/review`)
  const payload = await parseJson<{ detail?: string } & ReviewReport>(response)
  if (!response.ok) throw new Error(payload?.detail || "Review report is not available.")
  return payload as ReviewReport
}

export async function fetchPreview(jobId: string): Promise<DocumentPreview> {
  const response = await fetch(`/jobs/${jobId}/preview`)
  const payload = await parseJson<{ detail?: string } & DocumentPreview>(response)
  if (!response.ok) throw new Error(payload?.detail || "Document preview is not available.")
  return payload as DocumentPreview
}

export async function applyReviewEdits(jobId: string, edits: ReviewEdit[]): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`/jobs/${jobId}/edits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edits }),
    })
  } catch {
    throw new Error("Could not reach DocNA.")
  }
  const payload = await parseJson<{ detail?: string }>(response)
  if (!response.ok) throw new Error(payload?.detail || "Could not save changes.")
  return payload
}

export async function downloadCompletedDocx(jobId: string): Promise<Blob> {
  const response = await fetch(`/jobs/${jobId}/download`)
  if (!response.ok) throw new Error("Download failed.")
  return response.blob()
}

export async function sendAssistMessage(
  jobId: string,
  taskId: string,
  message: string,
  history: AssistMessage[],
): Promise<AssistResponse> {
  const response = await fetch(`/jobs/${jobId}/tasks/${taskId}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  })
  const payload = await parseJson<{ detail?: string } & AssistResponse>(response)
  if (!response.ok) throw new Error(payload?.detail || "AI assistance failed.")
  return payload as AssistResponse
}

export async function fetchWorkspaces(): Promise<WorkspacesListResponse> {
  const response = await fetch("/workspaces")
  const payload = await parseJson<{ detail?: string } & WorkspacesListResponse>(response)
  if (!response.ok) throw new Error(payload?.detail || "Couldn't load your documents.")
  return payload as WorkspacesListResponse
}

export async function fetchWorkspace(workspaceId: string): Promise<WorkspaceSummary> {
  const response = await fetch(`/workspaces/${workspaceId}`)
  const payload = await parseJson<{ detail?: string } & WorkspaceSummary>(response)
  if (!response.ok) throw new Error(payload?.detail || "Workspace not found.")
  return payload as WorkspaceSummary
}

export async function fetchWorkspaceReview(workspaceId: string): Promise<ReviewReport> {
  const response = await fetch(`/workspaces/${workspaceId}/review`)
  const payload = await parseJson<{ detail?: string } & ReviewReport>(response)
  if (!response.ok) throw new Error(payload?.detail || "Review report is not available.")
  return payload as ReviewReport
}

export async function saveWorkspaceEdits(workspaceId: string, edits: ReviewEdit[]): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`/workspaces/${workspaceId}/edits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edits }),
    })
  } catch {
    throw new Error("Could not reach DocNA.")
  }
  const payload = await parseJson<{ detail?: string }>(response)
  if (!response.ok) throw new Error(payload?.detail || "Could not save changes.")
  return payload
}

export async function renameWorkspace(workspaceId: string, displayName: string): Promise<WorkspaceSummary> {
  const response = await fetch(`/workspaces/${workspaceId}/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  })
  const payload = await parseJson<{ detail?: string } & WorkspaceSummary>(response)
  if (!response.ok) throw new Error(payload?.detail || "Could not rename document.")
  return payload as WorkspaceSummary
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  const response = await fetch(`/workspaces/${workspaceId}`, { method: "DELETE" })
  if (!response.ok) {
    const payload = await parseJson<{ detail?: string }>(response)
    throw new Error(payload?.detail || "Could not delete document.")
  }
}
