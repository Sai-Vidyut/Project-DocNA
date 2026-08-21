import { useCallback, useEffect, useRef, useState } from "react"
import { AppShell } from "@/components/layout/AppShell"
import { CosmicBackground } from "@/components/layout/CosmicBackground"
import { Header } from "@/components/layout/Header"
import { DocumentsView } from "@/components/documents/DocumentsView"
import { UploadView } from "@/components/upload/UploadView"
import { ProcessingView } from "@/components/processing/ProcessingView"
import { ReviewWorkspace } from "@/components/review/ReviewWorkspace"
import { ErrorView } from "@/components/error/ErrorView"
import { AskAIDialog } from "@/components/ai/AskAIDialog"
import {
  deleteWorkspace,
  downloadCompletedDocx,
  fetchJobStatus,
  fetchPreview,
  fetchWorkspace,
  fetchWorkspaceReview,
  fetchWorkspaces,
  renameWorkspace,
  saveWorkspaceEdits,
  sendAssistMessage,
  uploadDocument,
} from "@/lib/api"
import { TERMINAL_STATUSES } from "@/lib/constants"
import { defaultExportBasename, exportDownloadFilename } from "@/lib/export-filename"
import { isDocxFile } from "@/lib/format"
import { buildInitialAnswerState, collectQuestionCardItems } from "@/lib/review-utils"
import { persistActiveWorkspaceId } from "@/lib/session-storage"
import { useAutosave } from "@/lib/use-autosave"
import type {
  AppView,
  AssistMessage,
  DocumentPreview,
  JobStatus,
  ReviewReport,
  ReviewTaskEntry,
  WorkspaceSummary,
} from "@/lib/types"

export function DocNAApp() {
  const [view, setView] = useState<AppView>("documents")
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(true)
  const [documentsLoadFailed, setDocumentsLoadFailed] = useState(false)
  const [documentsError, setDocumentsError] = useState("")

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState("")
  const [analyzing, setAnalyzing] = useState(false)

  const [workspaceId, setWorkspaceId] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus>("queued")
  const pollRef = useRef<number | null>(null)
  const pollingJobIdRef = useRef<string | null>(null)

  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceSummary | null>(null)
  const [reviewReport, setReviewReport] = useState<ReviewReport | null>(null)
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [answerState, setAnswerState] = useState<Map<string, string>>(new Map())
  const [originalAnswers, setOriginalAnswers] = useState<Map<string, string>>(new Map())
  const [downloadReady, setDownloadReady] = useState(false)
  const [reviewError, setReviewError] = useState("")
  const [exportBasename, setExportBasename] = useState("")

  const [errorTitle, setErrorTitle] = useState("")
  const [errorDetail, setErrorDetail] = useState("")

  const [assistOpen, setAssistOpen] = useState(false)
  const [assistTask, setAssistTask] = useState<ReviewTaskEntry | null>(null)
  const [assistMessages, setAssistMessages] = useState<AssistMessage[]>([])
  const [assistHistory, setAssistHistory] = useState<AssistMessage[]>([])
  const [assistLoading, setAssistLoading] = useState(false)
  const [assistExample, setAssistExample] = useState<string | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
    pollingJobIdRef.current = null
  }, [])

  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true)
    setDocumentsLoadFailed(false)
    setDocumentsError("")
    try {
      const payload = await fetchWorkspaces()
      setWorkspaces(payload.workspaces)
    } catch (error) {
      setDocumentsLoadFailed(true)
      setDocumentsError(error instanceof Error ? error.message : "Couldn't load your documents.")
    } finally {
      setDocumentsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  const clearReviewUiState = useCallback(() => {
    setReviewReport(null)
    setPreview(null)
    setAnswerState(new Map())
    setOriginalAnswers(new Map())
    setDownloadReady(false)
    setReviewError("")
    setExportBasename("")
    setAssistOpen(false)
    setAssistTask(null)
    setAssistMessages([])
    setAssistHistory([])
    setAssistExample(null)
  }, [])

  const resetActiveWorkspace = useCallback(() => {
    stopPolling()
    setWorkspaceId(null)
    setJobId(null)
    setJobStatus("queued")
    setActiveWorkspace(null)
    persistActiveWorkspaceId(null)
    clearReviewUiState()
  }, [clearReviewUiState, stopPolling])

  const goToDocuments = useCallback(async () => {
    if (view === "review") await flushAutosaveRef.current()
    stopPolling()
    clearReviewUiState()
    setSelectedFile(null)
    setUploadError("")
    setAnalyzing(false)
    setWorkspaceId(null)
    setJobId(null)
    setActiveWorkspace(null)
    setJobStatus("queued")
    setView("documents")
    await loadDocuments()
  }, [clearReviewUiState, loadDocuments, stopPolling, view])

  const goToUpload = useCallback(async () => {
    if (view === "review") await flushAutosaveRef.current()
    stopPolling()
    resetActiveWorkspace()
    setSelectedFile(null)
    setUploadError("")
    setAnalyzing(false)
    setView("upload")
  }, [resetActiveWorkspace, stopPolling, view])

  const loadReview = useCallback(async (activeWorkspaceId: string) => {
    const [report, docPreview, workspace] = await Promise.all([
      fetchWorkspaceReview(activeWorkspaceId),
      fetchPreview(activeWorkspaceId),
      fetchWorkspace(activeWorkspaceId),
    ])
    const { answers, originals } = buildInitialAnswerState(report)

    setWorkspaceId(activeWorkspaceId)
    setJobId(activeWorkspaceId)
    setActiveWorkspace(workspace)
    persistActiveWorkspaceId(activeWorkspaceId)
    setReviewReport(report)
    setPreview(docPreview)
    setAnswerState(answers)
    setOriginalAnswers(originals)
    setDownloadReady(Boolean(report.download_ready))
    setExportBasename(defaultExportBasename(workspace.display_name + ".docx"))
    setReviewError("")
    setView("review")
  }, [])

  const handleAutosave = useCallback(
    async (edits: { task_id: string; text: string }[]) => {
      if (!workspaceId || edits.length === 0) return
      await saveWorkspaceEdits(workspaceId, edits)
      const workspace = await fetchWorkspace(workspaceId)
      setActiveWorkspace(workspace)
      setDownloadReady(workspace.download_ready)
      setOriginalAnswers((prev) => {
        const next = new Map(prev)
        for (const edit of edits) {
          const trimmed = edit.text.trim()
          if (trimmed) next.set(edit.task_id, trimmed)
        }
        return next
      })
    },
    [workspaceId],
  )

  const { status: autosaveStatus, lastSavedAt, queue: queueAutosave, flush: flushAutosave } = useAutosave({
    onSave: handleAutosave,
  })
  const flushAutosaveRef = useRef(flushAutosave)
  flushAutosaveRef.current = flushAutosave

  const handleTerminalStatus = useCallback(
    async (activeJobId: string, payload: { status: JobStatus; error_message?: string | null }) => {
      stopPolling()
      if (payload.status === "completed") {
        try {
          await loadReview(activeJobId)
        } catch (error) {
          setErrorTitle(error instanceof Error ? error.message : "Could not load review.")
          setErrorDetail("Try another document.")
          setView("error")
        }
        return
      }
      setErrorTitle("DocNA could not process this document.")
      setErrorDetail(payload.error_message || "Try another document.")
      setView("error")
    },
    [loadReview, stopPolling],
  )

  const pollJob = useCallback(
    async (activeJobId: string) => {
      try {
        const payload = await fetchJobStatus(activeJobId)
        setJobStatus(payload.status)
        if (TERMINAL_STATUSES.has(payload.status)) {
          await handleTerminalStatus(activeJobId, payload)
        }
      } catch (error) {
        stopPolling()
        setErrorTitle("DocNA could not process this document.")
        setErrorDetail(error instanceof Error ? error.message : "Try another document.")
        setView("error")
      }
    },
    [handleTerminalStatus, stopPolling],
  )

  const startPolling = useCallback(
    (activeJobId: string) => {
      if (pollingJobIdRef.current === activeJobId && pollRef.current !== null) return
      stopPolling()
      pollingJobIdRef.current = activeJobId
      void pollJob(activeJobId)
      pollRef.current = window.setInterval(() => void pollJob(activeJobId), 1000)
    },
    [pollJob, stopPolling],
  )

  useEffect(() => () => stopPolling(), [stopPolling])

  const resumeProcessing = useCallback(
    async (id: string, workspace: WorkspaceSummary) => {
      setActiveWorkspace(workspace)
      setWorkspaceId(id)
      setJobId(id)
      persistActiveWorkspaceId(id)
      setView("processing")
      try {
        const payload = await fetchJobStatus(id)
        setJobStatus(payload.status)
        if (TERMINAL_STATUSES.has(payload.status)) {
          await handleTerminalStatus(id, payload)
          return
        }
        startPolling(id)
      } catch {
        setJobStatus("processing")
        startPolling(id)
      }
    },
    [handleTerminalStatus, startPolling],
  )

  const openWorkspace = useCallback(
    async (id: string) => {
      setReviewError("")
      try {
        const workspace = await fetchWorkspace(id)
        setActiveWorkspace(workspace)
        setWorkspaceId(id)
        setJobId(id)
        persistActiveWorkspaceId(id)

        if (workspace.status === "failed") {
          setErrorTitle("Unable to process document")
          setErrorDetail(workspace.error_message || "Try another document.")
          setView("error")
          return
        }

        if (workspace.status === "processing") {
          await resumeProcessing(id, workspace)
          return
        }

        await loadReview(id)
      } catch (error) {
        setErrorTitle(error instanceof Error ? error.message : "Could not open document.")
        setErrorDetail("Return to your documents and try again.")
        setView("error")
      }
    },
    [loadReview, resumeProcessing],
  )

  const uploadAndProcess = useCallback(async (file: File) => {
    if (!isDocxFile(file)) {
      setUploadError("DocNA supports DOCX files only.")
      return
    }
    setSelectedFile(file)
    setAnalyzing(true)
    setUploadError("")
    try {
      const payload = await uploadDocument(file)
      const id = payload.workspace_id || payload.job_id
      setWorkspaceId(id)
      setJobId(id)
      setJobStatus(payload.status || "queued")
      persistActiveWorkspaceId(id)
      setActiveWorkspace({
        workspace_id: id,
        job_id: id,
        document_name: file.name,
        display_name: file.name.replace(/\.docx$/i, "") || "Document",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: "processing",
        questions_detected: 0,
        answers_generated: 0,
        items_remaining: 0,
        items_needing_review: 0,
        edited_task_ids: [],
        export_filename: `${file.name.replace(/\.docx$/i, "") || "Document"}_completed.docx`,
        download_ready: false,
      })
      setView("processing")
      startPolling(id)
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Could not upload this file.")
    } finally {
      setAnalyzing(false)
    }
  }, [startPolling])

  const handleSelectFile = (file: File | null) => {
    setUploadError("")
    if (!file) {
      setSelectedFile(null)
      return
    }
    if (!isDocxFile(file)) {
      setUploadError("DocNA supports DOCX files only.")
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
  }

  const handleAnalyze = async () => {
    if (!selectedFile) return
    await uploadAndProcess(selectedFile)
  }

  const handleQuickUpload = (file: File) => {
    void uploadAndProcess(file)
  }

  const handleAnswerChange = (taskId: string, text: string) => {
    setAnswerState((prev) => {
      const next = new Map(prev)
      next.set(taskId, text)
      return next
    })
    if (downloadReady) setDownloadReady(false)
    queueAutosave(taskId, text)
  }

  useEffect(() => {
    if (view !== "review") return
    return () => {
      void flushAutosave()
    }
  }, [view, flushAutosave])

  const handleDownload = async () => {
    if (!jobId || !downloadReady) return
    await flushAutosave()
    try {
      const blob = await downloadCompletedDocx(jobId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = exportDownloadFilename(exportBasename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Download failed.")
    }
  }

  const handleDeleteWorkspace = async (id: string): Promise<void> => {
    await deleteWorkspace(id)
    if (workspaceId === id) {
      resetActiveWorkspace()
      setView("documents")
    }
    await loadDocuments()
  }

  const openAskAI = (item: ReviewTaskEntry, _anchor: HTMLElement) => {
    setAssistTask(item)
    setAssistMessages([])
    setAssistHistory([])
    setAssistExample(null)
    setAssistOpen(true)
  }

  const closeAskAI = () => setAssistOpen(false)

  const handleAssistSend = async (message: string) => {
    if (!jobId || !assistTask) return
    setAssistMessages((prev) => [...prev, { role: "user", content: message }])
    setAssistLoading(true)
    try {
      const payload = await sendAssistMessage(jobId, assistTask.task_id, message, assistHistory)
      const nextHistory: AssistMessage[] = [
        ...assistHistory,
        { role: "user", content: message },
        { role: "assistant", content: payload.message },
      ]
      setAssistHistory(nextHistory)
      setAssistMessages((prev) => [...prev, { role: "assistant", content: payload.message }])
      if (payload.example_response) setAssistExample(payload.example_response)
    } catch (error) {
      setAssistMessages((prev) => [
        ...prev,
        { role: "assistant", content: error instanceof Error ? error.message : "AI assistance failed." },
      ])
    } finally {
      setAssistLoading(false)
    }
  }

  const useAssistExample = () => {
    if (!assistTask || !assistExample) return
    handleAnswerChange(assistTask.task_id, assistExample)
    setAssistOpen(false)
  }

  const filename =
    preview?.filename || activeWorkspace?.document_name || selectedFile?.name || ""
  const headerStatus =
    view === "processing"
      ? jobStatus === "completed"
        ? "Ready"
        : "Processing"
      : view === "review"
        ? downloadReady
          ? "Ready"
          : "Review"
        : ""

  const attentionItems = reviewReport ? collectQuestionCardItems(reviewReport) : []

  return (
    <>
      <CosmicBackground />
      <Header
        view={view}
        filename={view === "documents" || view === "upload" ? undefined : filename}
        status={headerStatus}
        onNewDocument={goToUpload}
        onDocuments={view === "documents" ? undefined : goToDocuments}
        hideNewDocument={view === "processing"}
      />
      <AppShell>
        {view === "documents" ? (
          <DocumentsView
            workspaces={workspaces}
            loading={documentsLoading}
            loadFailed={documentsLoadFailed}
            error={documentsError}
            onRefresh={() => void loadDocuments()}
            onNewDocument={goToUpload}
            onDropFile={handleQuickUpload}
            onOpen={(id) => void openWorkspace(id)}
            onRename={async (id, displayName) => {
              await renameWorkspace(id, displayName)
              await loadDocuments()
            }}
            onDelete={handleDeleteWorkspace}
          />
        ) : null}

        {view === "upload" ? (
          <UploadView
            selectedFile={selectedFile}
            error={uploadError}
            analyzing={analyzing}
            onSelectFile={handleSelectFile}
            onAnalyze={handleAnalyze}
            onBack={goToDocuments}
          />
        ) : null}

        {view === "processing" ? (
          <ProcessingView
            filename={selectedFile?.name || activeWorkspace?.document_name || "Document"}
            status={jobStatus}
            questionCount={activeWorkspace?.questions_detected}
          />
        ) : null}

        {view === "review" && reviewReport && preview ? (
          <ReviewWorkspace
            report={reviewReport}
            preview={preview}
            attentionItems={attentionItems}
            answerState={answerState}
            originalAnswers={originalAnswers}
            downloadReady={downloadReady}
            reviewError={reviewError}
            autosaveStatus={autosaveStatus}
            lastSavedAt={lastSavedAt}
            exportBasename={exportBasename}
            onExportBasenameChange={setExportBasename}
            onAnswerChange={handleAnswerChange}
            onAskAI={openAskAI}
            onDownload={handleDownload}
            onRestart={goToDocuments}
          />
        ) : null}

        {view === "error" ? (
          <ErrorView title={errorTitle} detail={errorDetail} onRetry={goToDocuments} />
        ) : null}
      </AppShell>

      <AskAIDialog
        open={assistOpen}
        task={assistTask}
        loading={assistLoading}
        messages={assistMessages}
        exampleResponse={assistExample}
        onClose={closeAskAI}
        onSend={handleAssistSend}
        onUseExample={useAssistExample}
        onWriteAnswer={() => setAssistOpen(false)}
      />
    </>
  )
}
