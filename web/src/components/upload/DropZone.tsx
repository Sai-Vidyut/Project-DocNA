import { useRef, useState, type DragEvent, type KeyboardEvent } from "react"
import { motion, useReducedMotion } from "motion/react"
import { springSoft, instantTransition } from "@/lib/motion-presets"
import { Upload } from "lucide-react"
import { cn } from "@/lib/utils"

interface DropZoneProps {
  onSelectFile: (file: File) => void
}

export function DropZone({ onSelectFile }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const reduce = useReducedMotion()

  const pick = () => inputRef.current?.click()

  const handleKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      pick()
    }
  }

  const acceptFile = (file: File | undefined) => {
    if (file) onSelectFile(file)
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    acceptFile(event.dataTransfer.files?.[0])
  }

  return (
    <>
      <motion.div
        role="button"
        tabIndex={0}
        aria-label="Drop your document here or choose a file"
        onClick={pick}
        onKeyDown={handleKey}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        initial={reduce ? false : { opacity: 0, y: 12, scale: 0.98 }}
        animate={{
          opacity: 1,
          y: 0,
          scale: dragOver && !reduce ? 1.02 : 1,
          borderColor: dragOver ? "hsla(var(--primary) / 0.28)" : undefined,
        }}
        whileHover={reduce ? undefined : { scale: 1.01 }}
        whileTap={reduce ? undefined : { scale: 0.995 }}
        transition={reduce ? instantTransition : springSoft}
        className={cn(
          "glass-1 relative cursor-pointer overflow-hidden rounded-md px-5 py-8 text-center",
          "hover:border-[hsla(var(--primary)/0.2)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.35)]",
          dragOver && "border-[hsla(var(--primary)/0.22)] bg-[hsla(var(--primary)/0.04)]",
        )}
      >
        <Upload className="mx-auto mb-2.5 size-7 text-[hsla(var(--primary)/0.8)]" aria-hidden strokeWidth={1.5} />
        <p className="m-0 text-sm font-medium text-[hsl(var(--foreground))]">Drop your document here</p>
        <p className="mt-1 text-[0.8125rem] text-[hsl(var(--muted))]">
          or <span className="text-[hsl(var(--primary))]">choose a file</span>
        </p>
        <p className="mt-2.5 type-meta">DOCX files only · Your original document is never modified</p>
      </motion.div>
      <input
        ref={inputRef}
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        hidden
        onChange={(e) => acceptFile(e.target.files?.[0])}
      />
    </>
  )
}
