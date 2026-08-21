import { useCallback, useEffect, useRef, useState } from "react"

export type AutosaveStatus = "idle" | "saving" | "saved" | "error"

interface UseAutosaveOptions {
  delayMs?: number
  onSave: (edits: { task_id: string; text: string }[]) => Promise<void>
}

export function useAutosave({ delayMs = 800, onSave }: UseAutosaveOptions) {
  const [status, setStatus] = useState<AutosaveStatus>("idle")
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const timerRef = useRef<number | null>(null)
  const pendingRef = useRef<Map<string, string>>(new Map())
  const savingRef = useRef(false)

  const flush = useCallback(async () => {
    if (savingRef.current || pendingRef.current.size === 0) return
    const batch = Array.from(pendingRef.current.entries()).map(([task_id, text]) => ({
      task_id,
      text,
    }))
    pendingRef.current.clear()
    savingRef.current = true
    setStatus("saving")
    try {
      await onSave(batch)
      setStatus("saved")
      setLastSavedAt(new Date())
    } catch {
      for (const edit of batch) {
        pendingRef.current.set(edit.task_id, edit.text)
      }
      setStatus("error")
    } finally {
      savingRef.current = false
    }
  }, [onSave])

  const queue = useCallback(
    (taskId: string, text: string) => {
      pendingRef.current.set(taskId, text)
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null
        void flush()
      }, delayMs)
    },
    [delayMs, flush],
  )

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    },
    [],
  )

  return { status, lastSavedAt, queue, flush }
}
