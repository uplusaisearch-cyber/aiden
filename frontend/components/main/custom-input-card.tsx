"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export interface CustomInputPayload {
  topic: string;
  options: {
    maxIter: 1 | 2 | 3;
    skipJudge: boolean;
    safetyMode: "normal" | "dry_run";
  };
}

interface Props {
  expanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onSubmit: (payload: CustomInputPayload) => void;
}

export function CustomInputCard({ expanded, onExpand, onCollapse, onSubmit }: Props) {
  const [topic, setTopic] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [maxIter, setMaxIter] = useState<1 | 2 | 3>(3);
  const [skipJudge, setSkipJudge] = useState(false);
  const [safetyMode, setSafetyMode] = useState<"normal" | "dry_run">("normal");

  if (!expanded) {
    return (
      <motion.button
        type="button"
        onClick={onExpand}
        whileHover={{ y: -2 }}
        whileTap={{ scale: 0.97 }}
        className="flex aspect-square flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border-strong bg-bg-elevated/60 p-4 text-text-secondary transition hover:border-accent-pink hover:text-text-primary"
      >
        <Pencil className="h-8 w-8 sm:h-10 sm:w-10" />
        <div className="text-center">
          <div className="font-korean text-sm font-semibold sm:text-base">자유 입력</div>
          <div className="hidden font-korean text-xs sm:block sm:text-sm">직접 주제 작성</div>
        </div>
      </motion.button>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-accent-pink bg-bg-elevated p-4 sm:p-6 col-span-2 sm:col-span-5"
      style={{ boxShadow: `0 0 24px var(--accent-pink-soft)` }}
    >
      <div className="mb-3 flex items-center justify-between">
        <label
          htmlFor="custom-topic"
          className="font-korean text-sm font-semibold text-text-primary sm:text-base"
        >
          어떤 주제로 콘텐츠를 만들까요?
        </label>
        <button
          type="button"
          onClick={onCollapse}
          className="rounded p-1 text-text-muted transition hover:text-text-primary"
          aria-label="자유 입력 닫기"
        >
          ✕
        </button>
      </div>

      <Input
        id="custom-topic"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="예: 30대 1인 가구를 위한 주말 야식 추천"
        className="font-korean"
      />

      <button
        type="button"
        onClick={() => setAdvancedOpen((v) => !v)}
        className="mt-3 inline-flex items-center gap-1 text-xs text-text-secondary transition hover:text-text-primary"
      >
        고급 옵션
        {advancedOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      <AnimatePresence initial={false}>
        {advancedOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 overflow-hidden"
          >
            <div className="grid gap-3 rounded-md border border-border-subtle bg-bg-secondary p-3 sm:grid-cols-3">
              <div>
                <div className="mb-1 text-xs text-text-muted">max_iter</div>
                <div className="flex gap-1">
                  {[1, 2, 3].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setMaxIter(n as 1 | 2 | 3)}
                      className={cn(
                        "rounded-md border px-2 py-1 text-xs transition",
                        maxIter === n
                          ? "border-accent-pink text-accent-pink"
                          : "border-border-subtle text-text-secondary hover:border-border-strong",
                      )}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-1 text-xs text-text-muted">Judge Panel</div>
                <label className="inline-flex items-center gap-2 text-xs text-text-secondary">
                  <input
                    type="checkbox"
                    checked={skipJudge}
                    onChange={(e) => setSkipJudge(e.target.checked)}
                  />
                  skip_judge
                </label>
              </div>
              <div>
                <div className="mb-1 text-xs text-text-muted">SAFETY_MODE</div>
                <div className="flex gap-1">
                  {(["normal", "dry_run"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setSafetyMode(m)}
                      className={cn(
                        "rounded-md border px-2 py-1 text-xs transition",
                        safetyMode === m
                          ? "border-accent-pink text-accent-pink"
                          : "border-border-subtle text-text-secondary hover:border-border-strong",
                      )}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
              <p className="font-korean text-[11px] text-text-muted sm:col-span-3">
                ⚠ <span className="font-mono">max_iter</span> / <span className="font-mono">SAFETY_MODE</span> 는 현재 동작하지 않습니다. 추가 개발 예정인 옵션입니다.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={!topic.trim()}
          onClick={() =>
            onSubmit({
              topic: topic.trim(),
              options: { maxIter, skipJudge, safetyMode },
            })
          }
          className={cn(
            "rounded-md px-4 py-2 text-sm font-semibold transition",
            topic.trim()
              ? "bg-accent-pink text-white hover:bg-accent-pink-hover"
              : "cursor-not-allowed bg-border-subtle text-text-muted",
          )}
        >
          Generate
        </button>
      </div>
    </motion.div>
  );
}
