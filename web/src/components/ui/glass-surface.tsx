import { cn } from "@/lib/utils"
import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react"
import { instantTransition, springSoft } from "@/lib/motion-presets"
import type { ReactNode } from "react"

export type GlassLevel = 0 | 1 | 2 | 3

interface GlassSurfaceProps extends Omit<HTMLMotionProps<"div">, "className"> {
  children: ReactNode
  level?: GlassLevel
  /** @deprecated use level={2} with hover styles on parent */
  glow?: boolean
  interactive?: boolean
  className?: string
}

const LEVEL_CLASS: Record<GlassLevel, string> = {
  0: "glass-0 rounded-md",
  1: "glass-1 rounded-md",
  2: "glass-2 rounded-md",
  3: "glass-3 rounded-lg",
}

export function GlassSurface({
  children,
  className,
  level = 2,
  glow,
  interactive,
  ...props
}: GlassSurfaceProps) {
  const reduce = useReducedMotion()

  return (
    <motion.div
      layout={!reduce}
      whileHover={interactive && !reduce ? { y: -2, scale: 1.005 } : undefined}
      transition={reduce ? instantTransition : springSoft}
      className={cn(
        LEVEL_CLASS[level],
        interactive && "hover:border-[hsla(var(--foreground)/0.1)]",
        glow && "border-[hsla(var(--primary)/0.14)] shadow-[0_4px_24px_hsla(228_40%_2%/0.35),0_0_20px_hsla(var(--ai-glow)/0.1)]",
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}
