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
  isLoading?: boolean;
  isError?: boolean;
  errorMessage?: string;
}

function scoreColor(weighted: number) {
  if (weighted >= 70) return "var(--state-success)";
  if (weighted >= 40) return "var(--state-warning)";
  return "var(--state-danger)";
}

// 백엔드는 RunStatus union 외 값(예: "failed_stage_1", "unknown")도 보낼 수 있으므로
// 알 수 없는 상태는 회색 폴백으로 표시 — UI 가 절대 크래시하지 않게.
function statusVariant(status: string) {
  if (status === "completed") return { label: "완료", color: "var(--state-success)" };
  if (status === "partial") return { label: "부분", color: "var(--state-warning)" };
  if (status === "running") return { label: "진행", color: "var(--state-info)" };
  if (status === "failed" || status.startsWith("failed"))
    return { label: "실패", color: "var(--state-danger)" };
  return { label: status || "—", color: "var(--text-muted)" };
}

function SkeletonGrid() {
  // 카드 자리에 6칸 pulse. 기존 카드와 동일 grid·간격·border 토큰 재사용.
  return (
    <div className="grid gap-3 sm:grid-cols-3" aria-busy="true" aria-live="polite">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-[136px] animate-pulse rounded-xl border border-border-subtle bg-bg-elevated"
        />
      ))}
    </div>
  );
}

export function RecentRuns({ runs, isLoading, isError, errorMessage }: Props) {
  const hasData = runs.length > 0;

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

      {/* 우선순위: 데이터 있음 > 로딩 > 에러 > 빈 상태.
          placeholderData 로 재요청 중에도 이전 데이터가 유지되면 깜빡임 없이 카드 노출. */}
      {hasData ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {runs.slice(0, 6).map((run, idx) => {
            const sv = statusVariant(run.status);
            return (
              <motion.div
                key={run.sessionId}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
              >
                <Link
                  href={`/admin/runs?preview=${encodeURIComponent(run.sessionId)}`}
                  className="group block rounded-xl border border-border-subtle bg-bg-elevated p-4 transition hover:-translate-y-0.5 hover:border-border-strong"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="font-korean text-xs"
                      style={{ borderColor: "var(--border-strong)" }}
                    >
                      {CATEGORY_LABEL_MAP[run.category] ?? run.category ?? "—"}
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
      ) : isLoading ? (
        <SkeletonGrid />
      ) : isError ? (
        <p className="font-korean text-xs text-state-danger">
          최근 실행을 불러오지 못했습니다 — 잠시 후 다시 시도해주세요.
          {errorMessage ? (
            <span className="ml-1 font-mono text-text-muted">({errorMessage})</span>
          ) : null}
        </p>
      ) : (
        <p className="font-korean text-sm text-text-muted">
          아직 생성된 콘텐츠가 없습니다.
        </p>
      )}
    </div>
  );
}
