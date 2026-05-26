import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "outline" | "ghost";

const VARIANT_CLASS: Record<Variant, string> = {
  default: "bg-accent-pink text-white",
  outline: "border border-border-subtle text-text-secondary",
  ghost: "bg-bg-secondary text-text-secondary",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        VARIANT_CLASS[variant],
        className,
      )}
      {...props}
    />
  );
}
