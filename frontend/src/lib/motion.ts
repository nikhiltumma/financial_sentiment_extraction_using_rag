import type { Transition, Variants } from 'framer-motion'

export const easeOut: Transition = { duration: 0.22, ease: [0.22, 1, 0.36, 1] }

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: easeOut },
}

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.03 } },
}

export const viewTransition: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.24, ease: 'easeOut' } },
  exit: { opacity: 0, y: -4, transition: { duration: 0.14 } },
}
