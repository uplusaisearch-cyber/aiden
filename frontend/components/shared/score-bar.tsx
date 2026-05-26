"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Props {
  value: number;
  max?: number;
  color?: string;
  showLabel?: boolean;
  className?: string;
}

function pickStateColor(value: number, max: number): string {
  const ratio = value / max;
  if (ratio >= 0.7) return "var(--state-success)";
  if (ratio >= 0.4) return "var(--state-warning)";
  return "var(--state-danger)";
}

export function ScoreBar({
  value,
  max = 10,
  color,
  showLabel = true,
  className,
}: Props) {
  const safeMax = Math.max(max, 0.001);
  const pct = Math.min(100, Math.max(0, (value / safeMax) * 100));
  const fill = color ?? pickStateColor(value, safeMax);

  return (
    <div className={cn("w-full", className)}>
      <div
        className="relative h-2 w-full overflow-hidden rounded-full"
        style={{ background: "var(--border-subtle)" }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: fill }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs text-text-muted">
          <span>{value.toFixed(1)}</span>
          <span>/ {max}</span>
        </div>
      )}
    </div>
  );
}
