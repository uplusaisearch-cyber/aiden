"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import type { MockRecentRun } from "@/types/run";
import { CATEGORY_LABEL_MAP } from "@/lib/constants";

interface Props {
  runs: MockRecentRun[];
}

function scoreColor(weighted: number) {
  if (weighted >= 70) return "var(--state-success)";
  if (weighted >= 40) return "var(--state-warning)";
  return "var(--state-danger)";
}

function statusVariant(status: MockRecentRun["status"]) {
  switch (status) {
    case "completed":
      return { label: "완료", color: "var(--state-success)" };
    case "partial":
      return { label: "부분", color: "var(--state-warning)" };
    case "failed":
      return { label: "실패", color: "var(--state-danger)" };
    case "running":
      return { label: "진행", color: "var(--state-info)" };
  }
}

export function RecentRuns({ runs }: Props) {
  return (
    <div className="w-full">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-korean text-lg font-semibold text-text-primary sm:text-xl">
          최근 실행
        </h2>
        <Link
          href="/admin/runs"
          className="text-xs text-text-secondary transition hover:text-accent-pink sm:text-sm"
        >
          전체 보기 →
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {runs.slice(0, 5).map((run, idx) => {
          const sv = statusVariant(run.status);
          return (
            <motion.div
              key={run.sessionId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
            >
              <Link
                href={`/run/${run.sessionId}`}
                className="group block rounded-xl border border-border-subtle bg-bg-elevated p-4 transition hover:-translate-y-0.5 hover:border-border-strong"
              >
                <div className="mb-2 flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="font-korean text-xs"
                    style={{ borderColor: "var(--border-strong)" }}
                  >
                    {CATEGORY_LABEL_MAP[run.category]}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-[10px]"
                    style={{ borderColor: sv.color, color: sv.color }}
                  >
                    {sv.label}
                  </Badge>
                </div>
                <h3 className="line-clamp-2 font-korean text-sm font-semibold text-text-primary group-hover:text-accent-pink sm:text-base">
                  {run.title}
                </h3>
                <div className="mt-3 flex items-baseline justify-between">
                  <span
                    className="font-mono text-xl font-bold sm:text-2xl"
                    style={{ color: scoreColor(run.weightedTotal) }}
                  >
                    {run.weightedTotal.toFixed(1)}
                    <span className="ml-0.5 text-xs text-text-muted">/100</span>
                  </span>
                  <span className="text-xs text-text-muted">
                    {formatDistanceToNow(new Date(run.finishedAt), {
                      addSuffix: true,
                      locale: ko,
                    })}
                  </span>
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
