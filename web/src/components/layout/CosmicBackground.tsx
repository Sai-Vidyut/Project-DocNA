import { motion, useReducedMotion } from "motion/react"

export function CosmicBackground() {
  const reduce = useReducedMotion()

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_-8%,hsla(228_50%_14%/0.5)_0%,transparent_50%),linear-gradient(180deg,hsl(228_44%_3%)_0%,hsl(var(--background))_40%,hsl(228_38%_5%)_100%)]" />
      <motion.div
        className="cosmic-ambient cosmic-ambient-a absolute rounded-full blur-[100px]"
        animate={reduce ? undefined : { opacity: [0.55, 0.75, 0.55], x: [0, 12, 0], y: [0, 8, 0] }}
        transition={{ duration: 42, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="cosmic-ambient cosmic-ambient-b absolute rounded-full blur-[100px]"
        animate={reduce ? undefined : { opacity: [0.45, 0.65, 0.45], x: [0, -10, 0], y: [0, -12, 0] }}
        transition={{ duration: 48, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="cosmic-ambient cosmic-ambient-c absolute rounded-full blur-[80px]"
        animate={reduce ? undefined : { opacity: [0.25, 0.4, 0.25] }}
        transition={{ duration: 36, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  )
}
