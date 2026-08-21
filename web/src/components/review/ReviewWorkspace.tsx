import { useCallback, useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import type { DocumentPreview, ReviewReport, ReviewTaskEntry } from "@/lib/types"
import { DocumentViewer } from "@/components/document/DocumentViewer"
import { DocumentToolbar } from "@/components/document/DocumentToolbar"
import { AttentionSection } from "./AttentionSection"
import { QuestionsComplete } from "./QuestionsComplete"
import { SaveStatus } from "./SaveStatus"
import { DocumentCanvas, ExportPanel } from "./ExportPanel"
import type { AutosaveStatus } from "@/lib/use-autosave"

const PAGE_WIDTH = 816
const ZOOM_STEPS = [0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5]

interface ReviewWorkspaceProps {
  report: ReviewReport
  preview: DocumentPreview
  attentionItems: ReviewTaskEntry[]
  answerState: Map<string, string>
  originalAnswers: Map<string, string>
  downloadReady: boolean
  reviewError: string
  autosaveStatus: AutosaveStatus
  lastSavedAt: Date | null
  exportBasename: string
  onExportBasenameChange: (value: string) => void
  onAnswerChange: (taskId: string, text: string) => void
  onAskAI: (item: ReviewTaskEntry, anchor: HTMLElement) => void
  onDownload: () => void
  onRestart: () => void
}

export function ReviewWorkspace({
  report,
  preview,
  attentionItems,
  answerState,
  originalAnswers,
  downloadReady,
  reviewError,
  autosaveStatus,
  lastSavedAt,
  exportBasename,
  onExportBasenameChange,
  onAnswerChange,
  onAskAI,
  onDownload,
  onRestart,
}: ReviewWorkspaceProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [scale, setScale] = useState(1)
  const [fitMode, setFitMode] = useState(true)

  const computeFitScale = useCallback(() => {
    const host = hostRef.current
    if (!host) return 1
    const available = host.clientWidth - 8
    return Math.min(1, Math.max(0.4, available / PAGE_WIDTH))
  }, [])

  useEffect(() => {
    if (!fitMode) return
    const update = () => setScale(computeFitScale())
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [fitMode, computeFitScale, preview])

  const zoomIn = () => {
    setFitMode(false)
    setScale((s) => {
      const next = ZOOM_STEPS.find((step) => step > s + 0.001) ?? ZOOM_STEPS[ZOOM_STEPS.length - 1]
      return next
    })
  }

  const zoomOut = () => {
    setFitMode(false)
    setScale((s) => {
      const prev = [...ZOOM_STEPS].reverse().find((step) => step < s - 0.001) ?? ZOOM_STEPS[0]
      return prev
    })
  }

  const zoomFit = () => {
    setFitMode(true)
    setScale(computeFitScale())
  }

  return (
    <section
      className="review-workspace flex min-h-[calc(100vh-var(--header-height))] flex-col xl:h-[calc(100vh-var(--header-height))] xl:min-h-0 xl:overflow-hidden"
      aria-labelledby="review-heading"
    >
      <h2 id="review-heading" ref={headingRef} tabIndex={-1} className="sr-only">
        Review workspace
      </h2>

      <div className="mx-auto flex w-full min-h-0 max-w-[1180px] flex-1 flex-col px-4 py-4 xl:overflow-hidden">
        <p id="preview-heading" className="sr-only">
          Document preview
        </p>

        {reviewError ? (
          <p className="mb-0 shrink-0 text-sm text-[hsl(var(--error))]" role="alert">
            {reviewError}
          </p>
        ) : null}

        <div
          className={`grid min-h-0 flex-1 grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_min(340px,32%)] xl:gap-6 xl:overflow-hidden ${reviewError ? "mt-2" : ""}`}
        >
          {/* Document workspace — independent scroll on desktop */}
          <div className="flex min-h-0 min-w-0 flex-col xl:overflow-hidden">
            <DocumentToolbar
              filename={preview.filename}
              downloadReady={downloadReady}
              zoomPercent={Math.round(scale * 100)}
              onZoomIn={zoomIn}
              onZoomOut={zoomOut}
              onZoomFit={zoomFit}
            />

            <div className="review-document-scroll mt-2.5 flex min-h-0 flex-1 flex-col gap-4 overflow-x-hidden xl:overflow-y-auto xl:overscroll-y-contain">
              <DocumentCanvas scale={scale} onContainerRef={(el) => { hostRef.current = el }}>
                <DocumentViewer
                  preview={preview}
                  answerState={answerState}
                  originalAnswers={originalAnswers}
                  onAnswerChange={onAnswerChange}
                />
              </DocumentCanvas>

              {downloadReady ? (
                <ExportPanel
                  exportBasename={exportBasename}
                  onBasenameChange={onExportBasenameChange}
                  onDownload={onDownload}
                />
              ) : (
                <SaveStatus
                  status={autosaveStatus}
                  lastSavedAt={lastSavedAt}
                  pendingInputCount={attentionItems.length}
                />
              )}
            </div>
          </div>

          {/* AI / review panel — independent scroll on desktop */}
          <aside
            className="review-questions-scroll flex min-h-0 flex-col gap-3 xl:overflow-y-auto xl:overscroll-y-contain"
            aria-label="Review controls"
          >
            <div className="sticky top-0 z-[1] space-y-1 bg-[hsla(var(--background)/0.85)] pb-2 backdrop-blur-md">
              <p className="type-section-label m-0">Review</p>
              <p className="m-0 text-[0.8125rem] text-[hsl(var(--foreground))]">
                {report.summary.questions_detected} questions
                {attentionItems.length > 0 ? (
                  <span className="text-[hsl(var(--muted))]">
                    {" "}
                    · {attentionItems.length} need your input
                  </span>
                ) : null}
              </p>
              <div className="workspace-divider pt-2" aria-hidden />
            </div>

            {attentionItems.length > 0 ? (
              <AttentionSection
                items={attentionItems}
                answerState={answerState}
                originalAnswers={originalAnswers}
                autosaveStatus={autosaveStatus}
                onAnswerChange={onAnswerChange}
                onAskAI={onAskAI}
              />
            ) : (
              <QuestionsComplete />
            )}

            <Button variant="ghost" block className="mt-1 text-xs text-[hsl(var(--muted))]" onClick={onRestart}>
              Back to documents
            </Button>
          </aside>
        </div>
      </div>
    </section>
  )
}
