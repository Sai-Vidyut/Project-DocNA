import { forwardRef } from "react"
import { cn } from "@/lib/utils"
import type { TextareaHTMLAttributes } from "react"

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  ai?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, ai, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full resize-y rounded border bg-[hsla(var(--background)/0.6)] px-2.5 py-2 text-sm leading-relaxed text-[hsl(var(--foreground))]",
        "placeholder:text-[hsl(var(--muted-foreground))]",
        "border-[hsla(var(--foreground)/0.08)] focus:outline-none focus:border-[hsla(var(--primary)/0.3)] focus:ring-2 focus:ring-[hsla(var(--primary)/0.08)]",
        ai && "focus:border-[hsla(var(--primary)/0.35)] focus:ring-[hsla(var(--primary)/0.1)]",
        className,
      )}
      {...props}
    />
  )
})
