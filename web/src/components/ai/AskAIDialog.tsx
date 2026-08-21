import { useEffect, useRef, useState } from "react"
import { Sparkles, X } from "lucide-react"
import { Dialog, DialogBackdrop } from "@/components/ui/dialog"
import { CosmicGlowButton } from "@/components/ui/spark-button"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { taskLabel } from "@/lib/format"
import type { AssistMessage, ReviewTaskEntry } from "@/lib/types"

interface AskAIDialogProps {
  open: boolean
  task: ReviewTaskEntry | null
  loading: boolean
  messages: AssistMessage[]
  exampleResponse: string | null
  onClose: () => void
  onSend: (message: string) => void
  onUseExample: () => void
  onWriteAnswer: () => void
}

export function AskAIDialog({
  open,
  task,
  loading,
  messages,
  exampleResponse,
  onClose,
  onSend,
  onUseExample,
  onWriteAnswer,
}: AskAIDialogProps) {
  const [input, setInput] = useState("")
  const messagesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) setInput("")
  }, [open, task?.task_id])

  useEffect(() => {
    if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight
  }, [messages, loading])

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const message = input.trim()
    if (message && !loading) {
      onSend(message)
      setInput("")
    }
  }

  if (!task) return null

  const hasConversation = messages.length > 0

  return (
    <>
      <DialogBackdrop open={open} onClose={onClose} />
      <Dialog open={open} onClose={onClose} labelledBy="assist-title" size="md">
        <div className="flex items-start justify-between gap-3 border-b border-[hsla(var(--foreground)/0.05)] px-4 py-3">
          <div className="min-w-0">
            <h3
              id="assist-title"
              className="m-0 flex items-center gap-1.5 text-[0.875rem] font-medium text-[hsl(var(--foreground))]"
            >
              <Sparkles className="size-3.5 shrink-0 text-[hsl(var(--primary))]" aria-hidden />
              Ask AI
            </h3>
            <p className="m-0 mt-0.5 truncate type-section-label">{taskLabel(task.task_text)}</p>
          </div>
          <button
            type="button"
            className="rounded p-1 text-[hsl(var(--muted))] transition-colors hover:bg-[hsla(var(--foreground)/0.05)] hover:text-[hsl(var(--foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.4)]"
            aria-label="Close"
            onClick={onClose}
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="border-b border-[hsla(var(--foreground)/0.05)] px-4 py-2.5">
          <p className="m-0 text-[0.8125rem] leading-snug text-[hsl(var(--foreground))]">{task.task_text}</p>
        </div>

        {hasConversation ? (
          <div
            ref={messagesRef}
            className="flex max-h-40 min-h-10 flex-col gap-2 overflow-auto px-4 py-3"
            aria-live="polite"
          >
            {messages.map((msg, index) => (
              <div
                key={index}
                className={
                  msg.role === "user"
                    ? "ml-auto max-w-[88%] rounded-md bg-[hsla(var(--primary)/0.1)] px-2.5 py-1.5 text-[0.78rem] leading-relaxed text-[hsl(var(--foreground))]"
                    : "max-w-[88%] rounded-md bg-[hsla(var(--foreground)/0.04)] px-2.5 py-1.5 text-[0.78rem] leading-relaxed text-[hsl(var(--foreground))]"
                }
              >
                {msg.content}
              </div>
            ))}
            {loading ? (
              <p className="m-0 type-meta" role="status">
                AI is thinking…
              </p>
            ) : null}
          </div>
        ) : (
          <div className="px-4 py-3">
            <p className="m-0 text-sm text-[hsl(var(--muted))]">What would you like help with?</p>
            {loading ? (
              <p className="mt-2 mb-0 type-meta" role="status">
                AI is thinking…
              </p>
            ) : null}
          </div>
        )}

        <form className="border-t border-[hsla(var(--foreground)/0.05)] px-4 py-3" onSubmit={submit}>
          <Textarea
            ai
            rows={2}
            className="min-h-0 w-full resize-none text-[0.8125rem]"
            value={input}
            disabled={loading}
            placeholder="Ask for clarification or help drafting your response…"
            aria-label="Message to AI assistant"
            onChange={(e) => setInput(e.target.value)}
          />
          <div className="mt-2 flex justify-end">
            <CosmicGlowButton compact type="submit" disabled={loading || !input.trim()}>
              Send
            </CosmicGlowButton>
          </div>
        </form>

        {(hasConversation || exampleResponse) && !loading ? (
          <div className="flex flex-wrap gap-2 border-t border-[hsla(var(--foreground)/0.05)] px-4 py-3">
            {exampleResponse ? (
              <>
                <p className="w-full m-0 type-meta">Example response (not your personal answer):</p>
                <p className="w-full m-0 rounded-md bg-[hsla(var(--foreground)/0.04)] px-2.5 py-2 text-[0.75rem] leading-relaxed">
                  {exampleResponse}
                </p>
                <Button variant="secondary" type="button" className="text-xs" onClick={onUseExample}>
                  Use this example
                </Button>
              </>
            ) : null}
            <Button variant="secondary" type="button" className="text-xs" onClick={onWriteAnswer}>
              Write answer manually
            </Button>
          </div>
        ) : null}
      </Dialog>
    </>
  )
}
