import { Check, Circle } from "lucide-react"
import { CURRENT_STATUS_LABEL, STAGE_ORDER, STATUS_TO_STAGE } from "@/lib/constants"
import type { JobStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ProcessingStepsProps {
  status: JobStatus
}

export function ProcessingSteps({ status }: ProcessingStepsProps) {
  const activeStage = STATUS_TO_STAGE[status] || "queued"
  const activeIndex = STAGE_ORDER.findIndex((stage) => stage.key === activeStage)
  const allDone = status === "completed"

  return (
    <ol className="m-0 list-none space-y-0 p-0 text-left" aria-label="Processing steps">
      {STAGE_ORDER.map((stage, index) => {
        const done = allDone || index < activeIndex
        const active = !allDone && index === activeIndex

        return (
          <li
            key={stage.key}
            className={cn(
              "flex items-center gap-2.5 py-1.5 text-[0.8125rem] leading-snug",
              done && "text-[hsl(var(--muted-foreground))]",
              active && "font-medium text-[hsl(var(--foreground))]",
              !done && !active && "text-[hsla(var(--muted-foreground)/0.65)]",
            )}
          >
            <span
              aria-hidden
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
            </span>
            <span>{stage.stepLabel}</span>
          </li>
        )
      })}
    </ol>
  )
}

export function currentProcessingLabel(status: JobStatus): string {
  return CURRENT_STATUS_LABEL[status] || "Processing"
}
