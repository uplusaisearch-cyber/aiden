"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { CategoryId } from "@/lib/constants";
import { CATEGORY_PRESETS } from "@/lib/constants";

interface Props {
  category: CategoryId;
  selected: boolean;
  onSelect: () => void;
}

const PRESET_MAP = Object.fromEntries(
  CATEGORY_PRESETS.map((p) => [p.id, p])
) as Record<string, (typeof CATEGORY_PRESETS)[number]>;

export function CategoryCard({ category, selected, onSelect }: Props) {
  const preset = PRESET_MAP[category];
  if (!preset) return null;

  return (
    <motion.button
      type="button"
      onClick={onSelect}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "group flex aspect-square flex-col items-center justify-center gap-2 rounded-xl border bg-bg-elevated p-4 text-left transition",
        selected
          ? "border-accent-pink"
          : "border-border-subtle hover:border-border-strong",
      )}
      style={
        selected
          ? { boxShadow: `0 0 0 1px var(--accent-pink), 0 0 24px var(--accent-pink-soft)`, background: "var(--accent-pink-soft)" }
          : undefined
      }
      aria-pressed={selected}
    >
      <motion.div
        whileHover={{ scale: 1.05 }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
        className="text-4xl sm:text-5xl"
      >
        {preset.icon}
      </motion.div>
      <div className="text-center">
        <div className="font-korean text-sm font-semibold text-text-primary sm:text-base">
          {preset.label}
        </div>
        <div className="hidden font-korean text-xs text-text-muted sm:block sm:text-sm">
          {preset.description}
        </div>
      </div>
    </motion.button>
  );
}
