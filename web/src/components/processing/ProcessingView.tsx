import type { JobStatus } from "@/lib/types"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { fadeUp, instantTransition, springSoft } from "@/lib/motion-presets"
import { ProcessingOrb } from "./ProcessingOrb"
import { ProcessingSteps, currentProcessingLabel } from "./ProcessingSteps"

interface ProcessingViewProps {
  filename: string
  status: JobStatus
  questionCount?: number
}

export function ProcessingView({ filename, status, questionCount }: ProcessingViewProps) {
  const activeLabel = currentProcessingLabel(status)
  const reduce = useReducedMotion()

  return (
    <section
      className="flex min-h-[calc(100vh-var(--header-height))] flex-col items-center justify-center px-4 py-8"
      aria-live="polite"
      aria-busy={status !== "completed" && status !== "failed"}
    >
      <motion.div
        className="w-full max-w-[22rem] text-center"
        initial={reduce ? false : "hidden"}
        animate="show"
        variants={fadeUp}
        transition={reduce ? instantTransition : springSoft}
      >
        <p className="m-0 truncate text-[0.9375rem] font-medium text-[hsl(var(--foreground))]">{filename}</p>

        <p className="mt-5 mb-0 type-section-label text-[hsl(var(--muted-foreground))]">
          Preparing your document
        </p>

        <ProcessingOrb activeLabel={activeLabel} />

        <AnimatePresence mode="wait">
          <motion.p
            key={activeLabel}
            className="m-0 text-[0.9375rem] font-medium text-[hsl(var(--foreground))]"
            role="status"
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, y: -4 }}
            transition={reduce ? instantTransition : { duration: 0.2 }}
          >
            {activeLabel}
          </motion.p>
        </AnimatePresence>
        {questionCount != null && questionCount > 0 ? (
          <p className="mt-1 mb-0 type-meta">
            {questionCount} question{questionCount === 1 ? "" : "s"} found
          </p>
        ) : null}

        <div className="mt-7 border-t border-[hsla(var(--foreground)/0.05)] pt-5">
          <ProcessingSteps status={status} />
        </div>

        <p className="mt-5 mb-0 type-meta">Longer documents may take a minute.</p>
      </motion.div>
    </section>
  )
}
