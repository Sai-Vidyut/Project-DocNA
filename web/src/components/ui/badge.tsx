import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "react"

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "default"
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
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
