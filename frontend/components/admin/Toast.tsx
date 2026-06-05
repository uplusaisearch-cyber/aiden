"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export type ToastKind = "success" | "error" | "info";

export interface ToastState {
  id: number;
  kind: ToastKind;
  text: string;
}

const KIND_CLASS: Record<ToastKind, string> = {
  success: "border-state-success/40 bg-state-success/15 text-state-success",
  error: "border-state-danger/50 bg-state-danger/15 text-state-danger",
  info: "border-accent-pink/40 bg-accent-pink-soft text-accent-pink",
};

interface Props {
  toasts: ToastState[];
}

export function ToastStack({ toasts }: Props) {
  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.18 }}
            className={cn(
              "pointer-events-auto min-w-[220px] max-w-xs rounded-md border px-4 py-2 font-korean text-sm shadow-lg",
              KIND_CLASS[t.kind],
            )}
          >
            {t.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

export function useToasts() {
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const counterRef = useRef(0);

  const push = useCallback((kind: ToastKind, text: string, ttlMs = 2400) => {
    counterRef.current += 1;
    const id = counterRef.current;
    setToasts((prev) => [...prev, { id, kind, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, ttlMs);
  }, []);

  return { toasts, push };
}
