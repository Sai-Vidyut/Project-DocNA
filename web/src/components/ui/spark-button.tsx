import { cn } from "@/lib/utils"
import type { ElementType, ComponentPropsWithoutRef, ReactNode } from "react"
import { Sparkles } from "lucide-react"

interface CosmicGlowButtonProps<T extends ElementType> {
  as?: T
  color?: string
  speed?: string
  className?: string
  children?: ReactNode
  compact?: boolean
  showIcon?: boolean
}

export function CosmicGlowButton<T extends ElementType = "button">({
  as,
  className,
  color,
  speed = "6s",
  children,
  compact,
  showIcon = true,
  ...props
}: CosmicGlowButtonProps<T> & Omit<ComponentPropsWithoutRef<T>, keyof CosmicGlowButtonProps<T>>) {
  const Component = as || "button"
  const glowColor = color || "hsl(var(--primary))"

  return (
    <Component
      className={cn(
        "relative inline-flex items-center justify-center overflow-hidden rounded-md border border-[hsla(var(--foreground)/0.08)] font-medium text-white cursor-pointer",
        "bg-[hsla(var(--surface-elevated)/0.85)]",
        "shadow-[0_2px_12px_hsla(228_40%_2%/0.4)] transition-[transform,box-shadow] duration-200",
        "hover:shadow-[0_4px_20px_hsla(228_40%_2%/0.5),0_0_16px_hsla(var(--ai-glow)/0.15)]",
        "active:scale-[0.99] motion-reduce:active:scale-100",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.45)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]",
        "disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:shadow-[0_2px_12px_hsla(228_40%_2%/0.4)]",
        compact ? "gap-1 px-3 py-1.5 text-xs" : "gap-1.5 px-4 py-2 text-sm",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-md opacity-30 animate-glow-scale motion-reduce:animate-none"
        style={{
          background: `radial-gradient(circle at 50% 120%, ${glowColor} 0%, transparent 65%)`,
          animationDuration: speed,
          zIndex: 0,
        }}
      />
      <span className="relative z-10 inline-flex items-center gap-1.5">
        {showIcon ? <Sparkles className="size-3.5 shrink-0 opacity-85" aria-hidden /> : null}
        {children}
      </span>
    </Component>
  )
}
