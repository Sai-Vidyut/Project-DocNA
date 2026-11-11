import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { Pencil, Trash2 } from "lucide-react"
import { instantTransition, menuPanel, springSnappy } from "@/lib/motion-presets"
import { cn } from "@/lib/utils"

interface DocumentMenuProps {
  open: boolean
  anchorRef: React.RefObject<HTMLElement | null>
  onClose: () => void
  onRename: () => void
  onDelete: () => void
}

export function DocumentMenu({ open, anchorRef, onClose, onRename, onDelete }: DocumentMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const reduce = useReducedMotion()

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return

    const update = () => {
      const anchor = anchorRef.current
      const menu = menuRef.current
      if (!anchor) return

      const rect = anchor.getBoundingClientRect()
      const menuHeight = menu?.offsetHeight ?? 88
      const menuWidth = menu?.offsetWidth ?? 140
      const gap = 6

      let top = rect.bottom + gap
      let left = rect.right - menuWidth

      if (top + menuHeight > window.innerHeight - 8) {
        top = rect.top - menuHeight - gap
      }
      if (left < 8) left = 8
      if (left + menuWidth > window.innerWidth - 8) {
        left = window.innerWidth - menuWidth - 8
      }

      setPosition({ top, left })
    }

    update()
    window.addEventListener("resize", update)
    window.addEventListener("scroll", update, true)
    return () => {
      window.removeEventListener("resize", update)
      window.removeEventListener("scroll", update, true)
    }
  }, [open, anchorRef])

  useEffect(() => {
    if (!open) return

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node
      if (menuRef.current?.contains(target)) return
      if (anchorRef.current?.contains(target)) return
      onClose()
    }

    document.addEventListener("keydown", onKey)
    document.addEventListener("mousedown", onPointer)
    return () => {
      document.removeEventListener("keydown", onKey)
      document.removeEventListener("mousedown", onPointer)
    }
  }, [open, onClose, anchorRef])

  return createPortal(
    <AnimatePresence>
      {open && position ? (
        <motion.div
          ref={menuRef}
          key="document-menu"
          role="menu"
          className={cn("glass-3 fixed z-[100] min-w-[9.5rem] rounded-md p-1")}
          style={{ top: position.top, left: position.left }}
          initial="hidden"
          animate="show"
          exit="exit"
          variants={menuPanel}
          transition={reduce ? instantTransition : springSnappy}
        >
          <motion.button
            type="button"
            role="menuitem"
            whileHover={reduce ? undefined : { x: 2 }}
            className="flex w-full items-center gap-2 rounded px-2.5 py-1.5 text-left text-[0.8125rem] text-[hsl(var(--foreground))] hover:bg-[hsla(var(--foreground)/0.05)] focus-visible:outline-none focus-visible:bg-[hsla(var(--foreground)/0.05)]"
            onClick={() => {
              onClose()
              onRename()
            }}
          >
            <Pencil className="size-3.5 text-[hsl(var(--muted))]" aria-hidden />
            Rename
          </motion.button>
          <motion.button
            type="button"
            role="menuitem"
            whileHover={reduce ? undefined : { x: 2 }}
            className="flex w-full items-center gap-2 rounded px-2.5 py-1.5 text-left text-[0.8125rem] text-[hsl(var(--error))] hover:bg-[hsla(var(--error)/0.08)] focus-visible:outline-none focus-visible:bg-[hsla(var(--error)/0.08)]"
            onClick={() => {
              onClose()
              onDelete()
            }}
          >
            <Trash2 className="size-3.5" aria-hidden />
            Delete
          </motion.button>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  )
}
