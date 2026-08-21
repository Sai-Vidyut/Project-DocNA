import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

interface AnswerRegionProps {
  taskId: string
  value: string
  editable: boolean
  edited: boolean
  onChange: (text: string) => void
}

export function AnswerRegion({ taskId, value, editable, edited, onChange }: AnswerRegionProps) {
  const [editing, setEditing] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  const beginEdit = () => {
    if (!editable || editing) return
    setEditing(true)
  }

  useEffect(() => {
    if (!editing || !ref.current) return
    ref.current.focus()
    const range = document.createRange()
    range.selectNodeContents(ref.current)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)

    const finish = () => {
      if (!ref.current) return
      setEditing(false)
      const text = ref.current.textContent?.trim() || ""
      if (!text) {
        ref.current.textContent = value
        return
      }
      onChange(text)
    }

    const node = ref.current
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        node.textContent = value
        finish()
      }
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault()
        finish()
      }
    }

    node.addEventListener("blur", finish)
    node.addEventListener("keydown", onKey)
    return () => {
      node.removeEventListener("blur", finish)
      node.removeEventListener("keydown", onKey)
    }
  }, [editing, onChange, value])

  if (!editable) {
    return <span className="preview-answer readonly">{value}</span>
  }

  return (
    <span
      ref={ref}
      data-task-id={taskId}
      role="textbox"
      tabIndex={0}
      aria-label="Editable answer"
      contentEditable={editing}
      suppressContentEditableWarning
      onClick={beginEdit}
      onKeyDown={(event) => {
        if (!editing && event.key === "Enter") {
          event.preventDefault()
          beginEdit()
        }
      }}
      className={cn("preview-answer", editing && "preview-answer-editing", edited && "preview-answer-edited")}
    >
      {value}
    </span>
  )
}
