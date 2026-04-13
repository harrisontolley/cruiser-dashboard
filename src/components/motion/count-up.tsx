"use client";

import { useEffect } from "react";
import {
  animate,
  motion,
  useMotionValue,
  useTransform,
  useReducedMotion,
} from "framer-motion";

interface CountUpProps {
  value: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}

export function CountUp({
  value,
  duration = 0.9,
  format = (n) => Math.round(n).toString(),
  className,
}: CountUpProps) {
  const prefersReducedMotion = useReducedMotion();
  const mv = useMotionValue(prefersReducedMotion ? value : 0);
  const display = useTransform(mv, (n) => format(n));

  useEffect(() => {
    if (prefersReducedMotion) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
    });
    return () => controls.stop();
  }, [value, duration, mv, prefersReducedMotion]);

  return <motion.span className={className}>{display}</motion.span>;
}
