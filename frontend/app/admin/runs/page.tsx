"use client";

/**
 * 출력 히스토리 — 영속 저장된 종료 run 결과 리스트.
 *
 * 명세: docs/patches/2026-06-05_output-history-persistence.md
 * 데이터 소스: GET /api/outputs (SQLite + Railway Volume 영속)
 * 트레이스/대화는 표시 X (범위 밖). 결과 메타 + final_html 미리보기/다운로드만.
 */

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  fetchOutputs,
  fetchOutputDetail,
  outputDownloadUrl,
  type OutputSummary,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<string, string> = {
  food: "맛집",
  "ai-trend": "AI 트렌드",
  safety: "안전",
  culture: "문화",
  custom: "자유 입력",
};

function scoreColor(weighted: number | null | undefined) {
  if (weighted == null) return "var(--text-muted)";
  if (weighted >= 70) return "var(--state-success)";
  if (weighted >= 40) return "var(--state-warning)";
  return "var(--state-danger)";
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatCost(usd: number | null): string {
  if (usd == null) return "—";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}

function formatTokens(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export default function RunHistoryPage() {
  // Next.js 14: useSearchParams 는 Suspense 경계 안이어야 prerender 가능.
  return (
    <Suspense fallback={<div className="font-korean text-sm text-text-muted">로딩 중…</div>}>
      <RunHistoryInner />
    </Suspense>
  );
}

function RunHistoryInner() {
  const searchParams = useSearchParams();
  const [previewRunId, setPreviewRunId] = useState<string | null>(null);

  // 메인 카드 클릭 → /admin/runs?preview=<runId> 진입 시 모달 자동 open.
  useEffect(() => {
    const q = searchParams.get("preview");
    if (q) setPreviewRunId(q);
  }, [searchParams]);

  const listQ = useQuery({
    queryKey: ["outputs", "list"],
    queryFn: () => fetchOutputs(50),
    staleTime: 30_000,
  });

  const outputs: OutputSummary[] = listQ.data?.outputs ?? [];
  const total = listQ.data?.total ?? 0;

  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-korean text-2xl font-bold text-text-primary">
            🗂️ 출력 히스토리
          </h1>
          <p className="mt-1 font-korean text-sm text-text-secondary">
            정상 종료된 run 의 결과 콘텐츠만 영속 저장됩니다 (트레이스/대화 제외).
            재배포에도 보존됩니다.
          </p>
        </div>
        <div className="font-mono text-xs text-text-muted">
          총 {total}건
        </div>
      </header>

      <div className="overflow-x-auto rounded-xl border border-border-subtle bg-bg-elevated">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left font-korean text-[11px] uppercase tracking-wider text-text-muted">
              <th className="px-4 py-2">토픽</th>
              <th className="px-3 py-2">카테고리</th>
              <th className="px-3 py-2">생성 시간</th>
              <th className="px-3 py-2 text-right">종합점수</th>
              <th className="px-3 py-2 text-right">토큰</th>
              <th className="px-3 py-2 text-right">비용</th>
              <th className="px-3 py-2 text-right">액션</th>
            </tr>
          </thead>
          <tbody>
            {listQ.isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center font-korean text-sm text-text-muted">
                  로딩 중…
                </td>
              </tr>
            )}
            {listQ.isError && !listQ.isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center font-korean text-sm text-state-danger">
                  목록 로드 실패: {(listQ.error as Error).message}
                </td>
              </tr>
            )}
            {!listQ.isLoading && !listQ.isError && outputs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center">
                  <div className="font-korean text-sm text-text-muted">
                    아직 저장된 결과가 없습니다.
                  </div>
                  <div className="mt-2 font-korean text-xs text-text-muted">
                    메인에서 Generate 후 정상 완료된 run 이 자동으로 적재됩니다.
                  </div>
                </td>
              </tr>
            )}
            {outputs.map((o) => (
              <tr key={o.run_id} className="border-b border-border-subtle/60 hover:bg-bg-secondary/40">
                <td className="max-w-md px-4 py-3 font-korean text-text-primary">
                  <div className="line-clamp-2">{o.topic ?? "(제목 없음)"}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-text-muted">
                    {o.run_id.slice(0, 20)}…
                  </div>
                </td>
                <td className="px-3 py-3 font-mono text-[11px] text-text-secondary">
                  {CATEGORY_LABEL[o.category ?? ""] ?? o.category ?? "—"}
                </td>
                <td className="px-3 py-3 font-mono text-[11px] text-text-muted">
                  {formatDateTime(o.created_at)}
                </td>
                <td className="px-3 py-3 text-right">
                  <span
                    className="font-mono text-base font-bold tabular-nums"
                    style={{ color: scoreColor(o.weighted_score) }}
                  >
                    {o.weighted_score != null ? o.weighted_score.toFixed(1) : "—"}
                  </span>
                </td>
                <td className="px-3 py-3 text-right font-mono text-xs tabular-nums text-text-secondary">
                  {formatTokens(o.total_tokens)}
                </td>
                <td className="px-3 py-3 text-right font-mono text-xs tabular-nums text-text-secondary">
                  <div className="flex items-center justify-end gap-1.5">
                    <span>{formatCost(o.total_cost_usd)}</span>
                    {o.cost_is_estimated && (
                      <Badge
                        variant="outline"
                        className="px-1 py-0 text-[9px] uppercase"
                        style={{
                          borderColor: "var(--state-warning)",
                          color: "var(--state-warning)",
                        }}
                        title="judge 토큰은 호출당 고정 추정값 사용 (실측 아님)"
                      >
                        est
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setPreviewRunId(o.run_id)}
                    >
                      미리보기
                    </Button>
                    <a
                      href={outputDownloadUrl(o.run_id)}
                      className={cn(
                        "inline-flex items-center justify-center rounded-md border border-border-subtle bg-bg-secondary px-3 py-1.5 font-korean text-xs text-text-secondary",
                        "transition hover:border-accent-pink hover:text-accent-pink",
                      )}
                      download
                    >
                      다운로드
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AnimatePresence>
        {previewRunId && (
          <PreviewModal runId={previewRunId} onClose={() => setPreviewRunId(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function PreviewModal({ runId, onClose }: { runId: string; onClose: () => void }) {
  const detailQ = useQuery({
    queryKey: ["outputs", "detail", runId],
    queryFn: () => fetchOutputDetail(runId),
    staleTime: 5 * 60_000,
  });

  const sizeKB =
    detailQ.data?.final_html != null
      ? (new Blob([detailQ.data.final_html]).size / 1024).toFixed(1)
      : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4 py-6"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.97, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.97, opacity: 0 }}
        className="flex h-full max-h-[90vh] w-full max-w-4xl flex-col rounded-xl border border-border-subtle bg-bg-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-border-subtle px-5 py-3">
          <div className="min-w-0">
            <h3 className="truncate font-korean text-base font-semibold text-text-primary">
              {detailQ.data?.topic ?? "(로딩 중)"}
            </h3>
            <p className="font-mono text-[10px] text-text-muted">
              {runId.slice(0, 24)}… {sizeKB ? `· ${sizeKB} KB` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {detailQ.data && (
              <a
                href={outputDownloadUrl(runId)}
                download
                className="rounded-md border border-border-subtle bg-bg-secondary px-3 py-1.5 font-korean text-xs text-text-secondary transition hover:border-accent-pink hover:text-accent-pink"
              >
                다운로드
              </a>
            )}
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              닫기
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-hidden bg-white">
          {detailQ.isLoading && (
            <div className="flex h-full items-center justify-center font-korean text-sm text-text-muted">
              로딩 중…
            </div>
          )}
          {detailQ.isError && (
            <div className="flex h-full items-center justify-center font-korean text-sm text-state-danger">
              로드 실패: {(detailQ.error as Error).message}
            </div>
          )}
          {detailQ.data && (
            <iframe
              srcDoc={detailQ.data.final_html}
              className="h-full w-full"
              // 인터랙티브(CHECKLIST/CALCULATOR) inline script 실행 필요.
              // srcDoc 은 별도 origin 으로 취급되어 allow-same-origin 없어도 안전.
              sandbox="allow-scripts"
              title={`Output preview: ${runId}`}
            />
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
