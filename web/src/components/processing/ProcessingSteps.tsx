import { Check, Circle } from "lucide-react"
import { motion, useReducedMotion } from "motion/react"
import { fadeUp, instantTransition, springSoft, staggerContainer } from "@/lib/motion-presets"
import { CURRENT_STATUS_LABEL, STAGE_ORDER, STATUS_TO_STAGE } from "@/lib/constants"
import type { JobStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ProcessingStepsProps {
  status: JobStatus
}

export function ProcessingSteps({ status }: ProcessingStepsProps) {
  const reduce = useReducedMotion()
  const activeStage = STATUS_TO_STAGE[status] || "queued"
  const activeIndex = STAGE_ORDER.findIndex((stage) => stage.key === activeStage)
  const allDone = status === "completed"

  return (
    <motion.ol
      className="m-0 list-none space-y-0 p-0 text-left"
      aria-label="Processing steps"
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={staggerContainer(0.08, 0.05)}
    >
      {STAGE_ORDER.map((stage, index) => {
        const done = allDone || index < activeIndex
        const active = !allDone && index === activeIndex

        return (
          <motion.li
            key={stage.key}
            variants={fadeUp}
            transition={reduce ? instantTransition : springSoft}
            layout
            className={cn(
              "flex items-center gap-2.5 py-1.5 text-[0.8125rem] leading-snug",
              done && "text-[hsl(var(--muted-foreground))]",
              active && "font-medium text-[hsl(var(--foreground))]",
              !done && !active && "text-[hsla(var(--muted-foreground)/0.65)]",
            )}
          >
            <motion.span
              aria-hidden
              animate={active && !reduce ? { scale: [1, 1.15, 1] } : undefined}
              transition={{ duration: 1.2, repeat: active ? Infinity : 0, ease: "easeInOut" }}
              className={cn(
                "flex size-[1.125rem] shrink-0 items-center justify-center",
                done && "text-[hsl(var(--success))]",
                active && "text-[hsl(var(--primary))]",
                !done && !active && "text-[hsla(var(--muted-foreground)/0.5)]",
              )}
            >
              {done ? (
                <Check className="size-3" strokeWidth={2.5} />
              ) : active ? (
                <Circle className="size-2 fill-current" />
              ) : (
                <Circle className="size-2" />
              )}
            </motion.span>
            <span>{stage.stepLabel}</span>
          </motion.li>
        )
      })}
    </motion.ol>
  )
}

export function currentProcessingLabel(status: JobStatus): string {
  return CURRENT_STATUS_LABEL[status] || "Processing"
}
