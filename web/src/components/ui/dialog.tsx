import { useEffect, useRef, type ReactNode } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { cn } from "@/lib/utils"
import { dialogBackdrop, dialogPanel, instantTransition, springSoft } from "@/lib/motion-presets"

interface DialogProps {
  open: boolean
  onClose: () => void
  children: ReactNode
  className?: string
  labelledBy?: string
  size?: "sm" | "md"
}

export function DialogBackdrop({ open, onClose }: { open: boolean; onClose: () => void }) {
  const reduce = useReducedMotion()

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          key="dialog-backdrop"
          className="fixed inset-0 z-40 bg-[hsla(228_42%_3%/0.72)] backdrop-blur-sm"
          aria-hidden="true"
          initial="hidden"
          animate="show"
          exit="exit"
          variants={dialogBackdrop}
          transition={reduce ? instantTransition : { duration: 0.2 }}
          onClick={onClose}
        />
      ) : null}
    </AnimatePresence>
  )
}

export function Dialog({ open, onClose, children, className, labelledBy, size = "sm" }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open || !panelRef.current) return
    const focusable = panelRef.current.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    focusable?.focus()
  }, [open])

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          ref={panelRef}
          key="dialog-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby={labelledBy}
          className={cn(
            "glass-dialog glass-3 fixed z-50 flex max-h-[min(80vh,520px)] flex-col overflow-hidden",
            size === "md" ? "w-[min(92vw,420px)]" : "w-[min(92vw,380px)]",
            className,
          )}
          style={{ top: "50%", left: "50%" }}
          initial="hidden"
          animate="show"
          exit="exit"
          variants={dialogPanel}
          transition={reduce ? instantTransition : springSoft}
        >
          {children}
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
