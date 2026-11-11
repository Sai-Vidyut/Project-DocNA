import { useEffect, useRef, type ReactNode } from "react"
import { motion, useReducedMotion } from "motion/react"
import { fadeUp, instantTransition, springSoft } from "@/lib/motion-presets"
import { CosmicGlowButton } from "@/components/ui/spark-button"
import { GlassSurface } from "@/components/ui/glass-surface"
import { exportDownloadFilename } from "@/lib/export-filename"

interface ExportPanelProps {
  exportBasename: string
  onBasenameChange: (value: string) => void
  onDownload: () => void
  downloading?: boolean
}

export function ExportPanel({ exportBasename, onBasenameChange, onDownload, downloading }: ExportPanelProps) {
  const invalid = !exportBasename.trim()
  const reduce = useReducedMotion()

  return (
    <motion.div
      className="export-finish"
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={fadeUp}
      transition={reduce ? instantTransition : springSoft}
    >
      <div className="workspace-divider mb-5" aria-hidden />
      <p className="type-section-label mb-1">Ready to export</p>
      <p className="m-0 text-sm text-[hsl(var(--muted))]">Your document is prepared.</p>

      <label htmlFor="export-filename" className="type-section-label mb-1.5 mt-4 block">
        Filename
      </label>
      <div className="flex max-w-md overflow-hidden rounded border border-[hsla(var(--foreground)/0.07)] bg-[hsla(var(--background)/0.35)] focus-within:border-[hsla(var(--primary)/0.28)]">
        <input
          id="export-filename"
          type="text"
          value={exportBasename}
          aria-describedby="export-filename-hint"
          className="min-w-0 flex-1 border-none bg-transparent px-2.5 py-1.5 text-sm text-[hsl(var(--foreground))] outline-none"
          onChange={(e) => onBasenameChange(e.target.value)}
        />
        <span className="flex items-center border-l border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--surface)/0.4)] px-2.5 text-sm text-[hsl(var(--muted))]">
          .docx
        </span>
      </div>
      <p id="export-filename-hint" className="mt-1 mb-0 type-meta">
        Saves as {exportDownloadFilename(exportBasename)}
      </p>

      <div className="mt-4 flex justify-end">
        <CosmicGlowButton type="button" disabled={invalid || downloading} onClick={onDownload}>
          Export document
        </CosmicGlowButton>
      </div>
    </motion.div>
  )
}

interface ApplyPanelProps {
  applying: boolean
  onApply: () => void
}

export function ApplyPanel({ applying, onApply }: ApplyPanelProps) {
  return (
    <GlassSurface level={1} className="px-4 py-3">
      <h3 className="m-0 text-sm font-medium text-[hsl(var(--foreground))]">Prepare download</h3>
      <p className="mt-1 mb-3 text-sm text-[hsl(var(--muted))]">Apply your edits to generate the completed document.</p>
      <CosmicGlowButton type="button" disabled={applying} onClick={onApply}>
        {applying ? "Applying…" : "Apply Changes & Prepare Download"}
      </CosmicGlowButton>
    </GlassSurface>
  )
}

interface DocumentCanvasProps {
  children: ReactNode
  scale: number
  onContainerRef?: (el: HTMLDivElement | null) => void
}

export function DocumentCanvas({ children, scale, onContainerRef }: DocumentCanvasProps) {
  const innerRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    onContainerRef?.(innerRef.current)
  }, [onContainerRef])

  return (
    <div ref={innerRef} className="document-stage document-canvas-host w-full overflow-x-auto overflow-y-visible pb-1">
      <motion.div
        className="document-canvas-scale mx-auto origin-top"
        style={{
          width: "816px",
          ["--doc-scale" as string]: scale,
        }}
        animate={{ scale }}
        transition={reduce ? instantTransition : springSoft}
      >
        <motion.article
          className="page-sheet"
          aria-label="Document page"
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={reduce ? instantTransition : { ...springSoft, delay: 0.06 }}
        >
          {children}
        </motion.article>
      </motion.div>
    </div>
  )
}
