import type { Transition, Variants } from "motion/react"

export const springSnappy = { type: "spring", stiffness: 440, damping: 34, mass: 0.82 } as const
export const springSoft = { type: "spring", stiffness: 300, damping: 28, mass: 0.92 } as const
export const springGentle = { type: "spring", stiffness: 220, damping: 26, mass: 1 } as const

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0 },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1 },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1 },
}

export const slideFromRight: Variants = {
  hidden: { opacity: 0, x: 18 },
  show: { opacity: 1, x: 0 },
}

export const viewTransition: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
}

export const dialogBackdrop: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1 },
  exit: { opacity: 0 },
}

export const dialogPanel: Variants = {
  hidden: { opacity: 0, scale: 0.96, x: "-50%", y: "calc(-50% + 10px)" },
  show: { opacity: 1, scale: 1, x: "-50%", y: "-50%" },
  exit: { opacity: 0, scale: 0.98, x: "-50%", y: "calc(-50% + 6px)" },
}

export const menuPanel: Variants = {
  hidden: { opacity: 0, scale: 0.94, y: -4 },
  show: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.96, y: -2 },
}

export const staggerContainer = (stagger = 0.055, delay = 0): Variants => ({
  hidden: {},
  show: {
    transition: { staggerChildren: stagger, delayChildren: delay },
  },
})

export const noMotionVariants: Variants = {
  hidden: {},
  show: {},
  initial: {},
  animate: {},
  exit: {},
}

export const instantTransition: Transition = { duration: 0 }

export const tapScale = { scale: 0.98 }
export const hoverLift = { y: -1 }
