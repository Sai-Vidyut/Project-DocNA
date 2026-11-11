import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react"
import {
  fadeUp,
  instantTransition,
  noMotionVariants,
  springSoft,
  staggerContainer,
  viewTransition,
} from "@/lib/motion-presets"

export function MotionPage({ children, className, ...props }: HTMLMotionProps<"div">) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={reduce ? noMotionVariants : viewTransition}
      transition={reduce ? instantTransition : springSoft}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function MotionReveal({
  children,
  className,
  delay = 0,
  ...props
}: HTMLMotionProps<"div"> & { delay?: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={fadeUp}
      transition={reduce ? instantTransition : { ...springSoft, delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function MotionStagger({ children, className, delay = 0, ...props }: HTMLMotionProps<"ul"> & { delay?: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.ul
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={reduce ? noMotionVariants : staggerContainer(0.05, delay)}
      className={className}
      {...props}
    >
      {children}
    </motion.ul>
  )
}

export function MotionStaggerItem({ children, className, ...props }: HTMLMotionProps<"li">) {
  const reduce = useReducedMotion()
  return (
    <motion.li
      variants={reduce ? noMotionVariants : fadeUp}
      transition={reduce ? instantTransition : springSoft}
      className={className}
      {...props}
    >
      {children}
    </motion.li>
  )
}
