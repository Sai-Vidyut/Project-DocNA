import { cn } from "@/lib/utils"
import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react"
import { instantTransition, springSnappy } from "@/lib/motion-presets"

interface BadgeProps extends Omit<HTMLMotionProps<"span">, "className"> {
  variant?: "success" | "warning" | "default"
  className?: string
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const reduce = useReducedMotion()

  return (
    <motion.span
      layout={!reduce}
      initial={reduce ? false : { opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={reduce ? instantTransition : springSnappy}
      className={cn(
        "inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[0.6875rem] font-medium",
        variant === "success" &&
          "bg-[hsla(var(--success)/0.1)] text-[hsl(var(--success))]",
        variant === "warning" &&
          "bg-[hsla(var(--warning)/0.1)] text-[hsl(var(--warning))]",
        variant === "default" &&
          "bg-[hsla(var(--foreground)/0.06)] text-[hsl(var(--muted))]",
        className,
      )}
      {...props}
    />
  )
}
